"""language.py - 입력 문장의 언어(한국어/영어) 판별. 어떤 감정 모델을 쓸지 정할 때 사용합니다.

글자 수가 아니라 '단어 수'로 비교합니다. 한글은 글자 하나가 음절 하나라서 글자 수로 세면 영어 쪽으로 치우칩니다.
  - 한글이 들어 있는 단어 vs 한글 없이 영문자만 있는 단어를 센다.
  - 한국어 단어가 같거나 더 많으면 "ko" (조사가 붙는 한국어 문장에 영어 단어가 섞인 경우를 한국어로 처리).
  - 글자가 하나도 없으면(이모지·숫자만) default를 쓴다.
"""
import re

SUPPORTED_LANGUAGES = ("ko", "en")
DEFAULT_LANGUAGE = "ko"

_HANGUL = re.compile(r"[가-힣ㄱ-ㅎㅏ-ㅣ]")
_LATIN = re.compile(r"[A-Za-z]")


def detect_language(text, default=DEFAULT_LANGUAGE):
    """텍스트 -> "ko" 또는 "en"."""
    korean_words = english_words = 0
    for word in text.split():
        if _HANGUL.search(word):
            korean_words += 1
        elif _LATIN.search(word):
            english_words += 1
    if korean_words == 0 and english_words == 0:
        return default
    return "ko" if korean_words >= english_words else "en"


def resolve_language(requested, text):
    """요청한 언어("ko"/"en")가 있으면 그대로, "auto"이거나 없으면 텍스트로 판별."""
    if requested in SUPPORTED_LANGUAGES:
        return requested
    return detect_language(text)
