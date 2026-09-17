"""Browser workflow for the high-school/adult self-assessment."""
import argparse
import os
import re
import time
import traceback
from dataclasses import dataclass
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from ai_answers import AnswerError, ROOT, make_answerer

EXAM_URL = "https://isafeevent.moe.edu.tw/exam/"
QUESTION_SELECTOR = '[id^="div_q_"]'
LIKERT_LABELS = {"非常同意", "同意", "普通", "不同意", "非常不同意"}


class QuizError(RuntimeError):
    pass


@dataclass
class Option:
    text: str
    radio: object
    label: object


@dataclass
class Question:
    id: str
    text: str
    options: list[Option]


def css_string(value):
    """Quote a value for use inside a CSS attribute selector."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\a ")
    return f'"{escaped}"'


def read_questions(driver):
    questions = []
    for block in driver.find_elements(By.CSS_SELECTOR, QUESTION_SELECTOR):
        if not block.is_displayed():
            continue
        radios = block.find_elements(By.CSS_SELECTOR, 'input[type="radio"]')
        if not radios:
            raise QuizError("出現非單選題或題目尚未載入；停止答題")
        headings = block.find_elements(By.CSS_SELECTOR, "h4")
        if len(headings) != 1 or not headings[0].text.strip():
            raise QuizError("無法辨識題目標題")
        options = []
        for radio in radios:
            radio_id = radio.get_attribute("id")
            matching = block.find_elements(By.CSS_SELECTOR, f"label[for={css_string(radio_id)}]") if radio_id else []
            if len(matching) != 1 or not matching[0].text.strip():
                raise QuizError("無法將選項文字對應至 radio；停止答題")
            options.append(Option(matching[0].text.strip(), radio, matching[0]))
        names = {radio.get_attribute("name") for radio in radios}
        if len(names) != 1 or not next(iter(names)) or len(options) < 2:
            raise QuizError("題目選項分組不符預期")
        questions.append(Question(block.get_attribute("id"), headings[0].text.strip(), options))
    if len({q.id for q in questions}) != len(questions):
        raise QuizError("題目 ID 重複")
    return questions


def signature(questions):
    return tuple((q.id, q.text, tuple(o.text for o in q.options)) for q in questions)


def wait_questions(driver, timeout=20, previous=None):
    def ready(_):
        try:
            questions = read_questions(driver)
            return questions if questions and signature(questions) != previous else False
        except StaleElementReferenceException:
            return False
    try:
        return WebDriverWait(driver, timeout).until(ready)
    except TimeoutException:
        raise QuizError("等待題目頁逾時；未繼續送出") from None


def select_option(driver, option, timeout=10):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", option.label)
    WebDriverWait(driver, timeout).until(lambda _: option.label.is_displayed() and option.label.is_enabled())
    option.label.click()
    WebDriverWait(driver, timeout).until(lambda _: option.radio.is_selected())


def click_button(driver, selector, timeout=20):
    def ready(_):
        buttons = [b for b in driver.find_elements(By.CSS_SELECTOR, selector) if b.is_displayed() and b.is_enabled()]
        if len(buttons) > 1:
            raise QuizError("同時出現多個送出／開始按鈕；停止操作")
        return buttons[0] if buttons else False
    button = WebDriverWait(driver, timeout).until(ready)
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", button)
    button.click()


def ensure_answered(questions):
    if not questions or any(sum(o.radio.is_selected() for o in q.options) != 1 for q in questions):
        raise QuizError("尚有題目未選取答案；不送出本頁")


def result_visible(driver):
    if any(e.is_displayed() for e in driver.find_elements(By.CSS_SELECTOR, QUESTION_SELECTOR)):
        return False
    headings = driver.find_elements(By.CSS_SELECTOR, "h1,h2,h3,h4")
    return any(e.is_displayed() and re.search(r"(?:評量|檢測|測驗)結果", e.text) for e in headings)


def complete_quiz(driver, answerer, *, timeout=20, exam_url=EXAM_URL):
    driver.get(exam_url)
    if "/login" in urlparse(driver.current_url).path:
        raise QuizError("尚未登入或登入已失效，請重新手動登入")
    click_button(driver, ".btnStartExam", timeout)
    first = wait_questions(driver, timeout)
    before = signature(first)
    for q in first:
        if {o.text for o in q.options} != LIKERT_LABELS or len(q.options) != 5:
            raise QuizError("第一頁不是預期的五點自我評量；請先確認網站流程")
    print(f"第一頁：{len(first)} 題，全部選普通", flush=True)
    for q in first:
        select_option(driver, next(o for o in q.options if o.text == "普通"), timeout)
    ensure_answered(first)
    click_button(driver, ".btnSendExam", timeout)
    second = wait_questions(driver, timeout, previous=before)
    if any({o.text for o in q.options} == LIKERT_LABELS for q in second):
        raise QuizError("仍停留在自我評量頁；停止操作")
    print(f"第二頁：{len(second)} 題，模型 {answerer.model}", flush=True)
    for i, q in enumerate(second, 1):
        choice = answerer.choose(q.text, [o.text for o in q.options])
        select_option(driver, q.options[choice], timeout)
        print(f"第 {i}/{len(second)} 題：選項 {choice + 1}", flush=True)
    ensure_answered(second)
    click_button(driver, ".btnSendExam", timeout)
    try:
        WebDriverWait(driver, timeout).until(result_visible)
    except TimeoutException:
        raise QuizError("已點擊最後送出，但未確認結果頁；請手動確認，勿自動重試以免重複提交") from None
    return True


def open_browser():
    os.environ.setdefault("SE_CACHE_PATH", str(ROOT / ".cache" / "selenium"))
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={ROOT / '.browser-profile'}")
    return webdriver.Chrome(options=options)


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("次數必須大於 0")
    return number


def nonnegative_int(value):
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("等待秒數不能小於 0")
    return number


def pause(prompt):
    # Used inside error handlers: a second Ctrl+C or closed stdin must not mask the original stop.
    try:
        input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()


def save_debug(driver):
    """Print the traceback and, when a browser is open, save a screenshot and page HTML under .cache/debug."""
    traceback.print_exc()
    if driver is None:
        return
    try:
        folder = ROOT / ".cache" / "debug"
        folder.mkdir(parents=True, exist_ok=True)
        stem = folder / time.strftime("%Y%m%d-%H%M%S")
        driver.save_screenshot(str(stem.with_suffix(".png")))
        stem.with_suffix(".html").write_text(driver.page_source, encoding="utf-8")
        print(f"除錯資料已存至 {stem}.png / .html（含頁面內容，請勿分享）", flush=True)
    except Exception as exc:
        print(f"無法儲存除錯資料：{type(exc).__name__}", flush=True)


def run(provider, argv=None):
    parser = argparse.ArgumentParser(description="2026 數位素養評量：手動登入後開始")
    parser.add_argument("--attempts", type=positive_int, default=1, help="評量次數，預設 1")
    parser.add_argument("--delay", type=nonnegative_int, default=10, help="兩次評量間隔秒數")
    parser.add_argument("--test-api", action="store_true", help="只呼叫一次 API 測試，不開啟網站")
    parser.add_argument("--debug", action="store_true", help="出錯時顯示 traceback，並將截圖與頁面 HTML 存到 .cache/debug")
    args = parser.parse_args(argv)
    driver = answerer = None
    try:
        if args.test_api:
            answerer = make_answerer(provider)
            if answerer.choose("為保護帳號安全，哪一項做法較好？", ["公開密碼", "啟用多因素驗證"]) != 1:
                raise AnswerError("API 可連線但未通過測試題")
            print(f"{provider} / {answerer.model} API 測試通過")
            return 0
        driver = open_browser()
        driver.get(EXAM_URL)
        input("請在開啟的 Chrome 手動登入（高中職以上／一般民眾），完成後回此視窗按 Enter 開始：")
        answerer = make_answerer(provider)
        successes = 0
        for attempt in range(args.attempts):
            complete_quiz(driver, answerer)
            successes += 1
            print(f"已確認結果頁：{successes}/{args.attempts}", flush=True)
            if attempt + 1 < args.attempts:
                time.sleep(args.delay)
        input("評量完成，按 Enter 關閉瀏覽器：")
        return 0
    except (AnswerError, QuizError) as exc:
        print(f"停止：{exc}", flush=True)
        if args.debug:
            save_debug(driver)
        if driver is not None:
            pause("請查看瀏覽器狀態，按 Enter 關閉：")
        return 1
    except (EOFError, KeyboardInterrupt):
        print("已取消")
        return 1
    except Exception as exc:
        hint = "" if args.debug else "；可加 --debug 查看詳細資訊"
        print(f"停止：{type(exc).__name__}；請檢查瀏覽器、網路及套件版本{hint}", flush=True)
        if args.debug:
            save_debug(driver)
        if driver is not None:
            pause("請查看瀏覽器狀態，按 Enter 關閉：")
        return 1
    finally:
        if answerer is not None:
            answerer.close()
        if driver is not None:
            driver.quit()
