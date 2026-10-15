import unittest
from unittest.mock import patch
from basic_bot import basic_reply
import test_app

class VarietyTests(unittest.TestCase):
    def ask(self,*texts):
        return basic_reply([{'role':'user','content':s} for s in texts])

    def test_topic_followups_keep_the_subject(self):
        self.assertIn('fruits[0]',self.ask('리스트가 뭐야?','예시 좀 보여줘'))
        self.assertIn('인덱스 1',self.ask('리스트가 뭐야?','예시 좀 보여줘','문제 하나 내줘'))
        self.assertIn('20이에요',self.ask('리스트가 뭐야?','예시 좀 보여줘','문제 하나 내줘','정답 알려줘'))
        self.assertIn('append',self.ask('리스트가 뭐야?','좀 더 자세하게 설명해줘'))

    def test_followups_do_not_reuse_an_unrelated_old_subject(self):
        reply=self.ask('리스트가 뭐야?','내일 날씨 알려줘','정답 알려줘')
        self.assertNotIn('20이에요',reply)
        self.assertIn('이 질문에 맞는 답을 만들 수는 없어요',reply)

    def test_specific_topic_beats_generic_word(self):
        self.assertIn('시간 복잡도',self.ask('알고리즘 시간복잡도 자세히 알려줘'))
        self.assertIn('def greet',self.ask('파이썬 함수 예시'))

    def test_comparisons(self):
        for question,expected in [('리스트와 튜플 차이','원소를 추가'),('Git과 GitHub 차이','호스팅'),('HTML과 CSS 차이','구조와 의미'),('스택과 큐 비교','FIFO')]:
            with self.subTest(question=question): self.assertIn(expected,self.ask(question))

    def test_general_subjects(self):
        for question,expected in [('광합성이 뭐야','빛 에너지'),('윤년 쉽게 설명해줘','2024'),('평균과 중앙값 차이','중앙값은 2'),('지구 자전과 공전','지구는 스스로 자전'),('현재완료 알려줘','have/has'),('회의록은 어떻게 써','담당자'),('여행 준비 체크리스트','예약 내역')]:
            with self.subTest(question=question): self.assertIn(expected,self.ask(question))

    def test_percentage_and_discount(self):
        self.assertIn('30이에요',self.ask('퍼센트: 200의 15%'))
        self.assertIn('30이에요',self.ask('200의 15%는 얼마야?'))
        self.assertIn('할인 후 금액: 40000',self.ask('50000원 20% 할인하면 얼마야?'))
        self.assertIn('0~100%',self.ask('할인: 50000, 120%'))

    def test_statistics_and_sorting(self):
        self.assertIn('평균: 20',self.ask('평균: 10, 20, 30'))
        self.assertIn('합계: -2',self.ask('합계: -5, 3'))
        self.assertIn('최댓값: 9',self.ask('최댓값: -1, 9, 3'))
        self.assertIn('최솟값: -1',self.ask('최솟값: -1, 9, 3'))
        self.assertIn('오름차순: 2, 5, 9',self.ask('정렬: 9, 2, 5'))
        self.assertIn('숫자를 쉼표',self.ask('평균: 사과, 배'))

    def test_bounded_numeric_inputs(self):
        self.assertIn('숫자를 쉼표',self.ask('평균: '+'1,'*101))
        self.assertIn('숫자를 쉼표',self.ask('합계: 1e100000'))
        self.assertIn('숫자를 쉼표',self.ask('평균: __import__("os")'))
        self.assertIn('콜론 뒤',self.ask('평균:'))

    def test_calendar_arithmetic(self):
        self.assertIn('2024-02-29',self.ask('날짜 더하기: 2024-02-28, 1'))
        self.assertIn('2027-01-01',self.ask('2026-12-25에서 7일 뒤는?'))
        self.assertIn('2026-10-08',self.ask('2026-10-15 7일 전'))
        self.assertIn('2일 뒤',self.ask('날짜 차이: 2024-02-28, 2024-03-01'))
        self.assertIn('존재하는 날짜',self.ask('날짜 더하기: 2025-02-29, 1'))
        self.assertIn('존재하는 날짜',self.ask('날짜 더하기: 9999-12-31, 1'))

    def test_text_lists(self):
        self.assertEqual(self.ask('중복 제거: 사과, 배, 사과'),'1. 사과\n2. 배')
        self.assertEqual(self.ask('대문자로: Hello world'),'HELLO WORLD')
        self.assertEqual(self.ask('소문자로: HELLO'),'hello')
        self.assertEqual(self.ask('목록 정리: 빨래, 공부'),'1. 빨래\n2. 공부')

    def test_templates_use_provided_fields(self):
        reply=self.ask('자기소개 작성: 이름=윤재; 분야=웹 개발; 경험=챗봇 제작; 목표=개발자')
        for value in ['윤재','웹 개발','챗봇 제작','개발자']: self.assertIn(value,reply)
        self.assertNotIn('수상',reply)
        self.assertIn('이름과 분야는 필수',self.ask('자기소개 작성: 이름=윤재'))
        reply=self.ask('이메일 작성: 받는사람=담당자; 주제=일정 문의; 내용=일정을 확인하고 싶습니다')
        self.assertIn('제목: 일정 문의',reply)
        self.assertIn('실제로 발송하지 않았어요',reply)

    def test_help_lists_real_commands(self):
        self.assertIn('퍼센트:',self.ask('도움말'))
        self.assertIn('날짜 차이:',self.ask('질문 예시'))
        self.assertIn('자기소개 작성:',self.ask('질문 예시'))

class VarietyApiTests(unittest.TestCase):
    setUpClass = classmethod(test_app.ChatTests.setUpClass.__func__)
    tearDownClass = classmethod(test_app.ChatTests.tearDownClass.__func__)
    session = test_app.ChatTests.session

    def test_end_to_end_followup_without_external_ai(self):
        with patch.object(self.main,'REPLY_MODE','basic'),patch.object(self.main.requests,'post',side_effect=AssertionError('External API forbidden')):
            sid=self.session()
            for text,expected in [('리스트가 뭐야?','자료구조'),('예시 좀 보여줘','fruits[0]'),('문제 하나 내줘','인덱스 1'),('정답 알려줘','20이에요'),('할인: 50000, 20%','40000'),('날짜 더하기: 2024-02-28, 1','2024-02-29')]:
                r=self.client.post(f'/sessions/{sid}/messages',json={'text':text})
                self.assertEqual(r.status_code,200)
                self.assertIn(expected,r.json()['reply'])
            self.assertEqual(len(self.client.get(f'/sessions/{sid}/messages').json()['messages']),12)
