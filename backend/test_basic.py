import unittest
from unittest.mock import patch
from basic_bot import basic_reply, calculate
import test_app

class BasicReplyTests(unittest.TestCase):
    def ask(self, *texts):
        return basic_reply([{'role':'user','content':text} for text in texts])

    def test_greeting_and_help(self):
        self.assertIn('기본 답변 모드', self.ask('안녕'))
        self.assertIn('외부 AI 없이', self.ask('뭐 할 수 있어?'))

    def test_name_memory(self):
        self.assertIn('윤재님',self.ask('내 이름은 윤재야','내 이름이 뭐야?'))
        self.assertIn('Alice님',self.ask('내 이름은 Alice','내 이름 기억해?'))
        self.assertIn('찾지 못했어요',self.ask('내 이름이 뭐야?'))

    def test_memos(self):
        self.assertIn('메모를 남겼어요',self.ask('메모: 회의'))
        reply=self.ask('메모: 회의','메모: 운동','메모 보여줘')
        self.assertIn('1. 회의',reply)
        self.assertIn('2. 운동',reply)
        self.assertIn('메모가 없어요',self.ask('메모 보여줘'))

    def test_arithmetic(self):
        for expression,expected in [('(12+8)*3','60'),('-5+2','-3'),('7/2','3.5'),('10%3','1'),('7//2','3')]:
            self.assertEqual(calculate(expression),expected)
        self.assertIn('= 60',self.ask('계산: (12 + 8) * 3'))

    def test_unsafe_and_excessive_arithmetic(self):
        for expression in ['__import__("os").getcwd()', '2**1000000', '[1]*9', 'True+1', '1/0', '9'*151, '1e10000']:
            with self.assertRaises((ValueError,SyntaxError,ZeroDivisionError)):
                calculate(expression)

    def test_unknown_does_not_fabricate_answer(self):
        self.assertIn('이 질문에 맞는 답을 만들 수는 없어요',self.ask('내일 날씨 알려줘'))

class OfflineApiTests(unittest.TestCase):
    setUpClass = classmethod(test_app.ChatTests.setUpClass.__func__)
    tearDownClass = classmethod(test_app.ChatTests.tearDownClass.__func__)
    session = test_app.ChatTests.session
    # Reuse isolated database fixture; run existing regression tests once in test_app.
    def test_offline_api_without_token_or_network(self):
        with patch.object(self.main,'REPLY_MODE','basic'), patch.dict('os.environ',{'HF_TOKEN':''}), patch.object(self.main.requests,'post',side_effect=AssertionError('Network must not be called')):
            h=self.client.get('/health').json()
            self.assertEqual(h['mode'],'basic')
            self.assertFalse(h['ai_configured'])
            sid=self.session()
            for text,contains in [('안녕','안녕하세요'),('내 이름은 윤재야','윤재님'),('내 이름이 뭐야?','윤재님'),('계산: 20 * 3','= 60'),('메모: 내일 회의','메모를 남겼어요'),('메모 보여줘','내일 회의')]:
                response=self.client.post(f'/sessions/{sid}/messages',json={'text':text})
                self.assertEqual(response.status_code,200)
                self.assertIn(contains,response.json()['reply'])
            self.assertEqual(len(self.client.get(f'/sessions/{sid}/messages').json()['messages']),12)
