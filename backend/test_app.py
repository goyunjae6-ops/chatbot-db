"""Run with: python -m unittest discover -s backend -p 'test_*.py'. Uses a temporary database."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import requests
from fastapi.testclient import TestClient

class ChatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.env = patch.dict(os.environ, {'CHAT_DB_PATH': str(Path(cls.temp.name) / 'test.db'), 'HF_TOKEN': 'test-token', 'CHAT_MODE': 'huggingface'})
        cls.env.start()
        base = Path(__file__).resolve().parent
        cls.previous_db = sys.modules.get('db')
        spec = importlib.util.spec_from_file_location('db', base / 'db.py')
        cls.db = importlib.util.module_from_spec(spec)
        sys.modules['db'] = cls.db
        spec.loader.exec_module(cls.db)
        spec = importlib.util.spec_from_file_location('chatbot_test_app', base / 'main.py')
        cls.main = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.main)
        cls.client = TestClient(cls.main.app)

    @classmethod
    def tearDownClass(cls):
        if cls.previous_db is None: sys.modules.pop('db', None)
        else: sys.modules['db'] = cls.previous_db
        cls.env.stop()
        cls.temp.cleanup()

    def session(self):
        response = self.client.post('/sessions')
        self.assertEqual(response.status_code, 200)
        return response.json()['id']

    def test_complete_conversation_and_memory(self):
        sid = self.session()
        with patch.object(self.main, 'ask_ai', return_value='안녕하세요') as ai:
            r = self.client.post(f'/sessions/{sid}/messages', json={'text': '내 이름은 윤재', 'request_id':'memory-1'})
            self.assertEqual(r.status_code, 200)
            self.client.post(f'/sessions/{sid}/messages', json={'text': '내 이름은?', 'request_id':'memory-2'})
            history = ai.call_args.args[0]
            self.assertEqual([m['role'] for m in history], ['user','assistant','user'])
            self.assertEqual(history[0]['content'], '내 이름은 윤재')
        self.assertEqual(len(self.client.get(f'/sessions/{sid}/messages').json()['messages']), 4)

    def test_failure_does_not_save_partial_exchange(self):
        sid=self.session()
        with patch.object(self.main.requests,'post',side_effect=requests.Timeout()):
            r=self.client.post(f'/sessions/{sid}/messages',json={'text':'실패 질문'})
        self.assertEqual(r.status_code,504)
        self.assertEqual(self.db.read_message(sid),[])

    def test_retry_is_idempotent(self):
        sid=self.session()
        body={'text':'한 번만 저장','request_id':'retry-test'}
        with patch.object(self.main,'ask_ai',return_value='답변') as ai:
            for _ in range(2): self.assertEqual(self.client.post(f'/sessions/{sid}/messages',json=body).status_code,200)
            self.assertEqual(ai.call_count,1)
        self.assertEqual(len(self.db.read_message(sid)),2)

    def test_reused_id_with_different_text_is_rejected(self):
        sid=self.session()
        with patch.object(self.main,'ask_ai',return_value='답변'):
            self.client.post(f'/sessions/{sid}/messages',json={'text':'첫 질문','request_id':'conflict'})
            r=self.client.post(f'/sessions/{sid}/messages',json={'text':'다른 질문','request_id':'conflict'})
        self.assertEqual(r.status_code,409)

    def test_missing_session(self):
        self.assertEqual(self.client.get('/sessions/999999/messages').status_code,404)
        self.assertEqual(self.client.post('/sessions/999999/messages',json={'text':'안녕'}).status_code,404)

    def test_invalid_messages(self):
        sid=self.session()
        for text in ['', '  ', 'x'*12001]:
            self.assertEqual(self.client.post(f'/sessions/{sid}/messages',json={'text':text}).status_code,422)

    def test_rename_delete_cascade(self):
        sid=self.session()
        self.assertEqual(self.client.put(f'/sessions/{sid}',json={'title':'새 제목'}).status_code,200)
        self.assertEqual(self.db.get_session(sid)['title'],'새 제목')
        with patch.object(self.main,'ask_ai',return_value='답변'):
            self.client.post(f'/sessions/{sid}/messages',json={'text':'질문','request_id':'delete-test'})
        self.assertEqual(self.client.delete(f'/sessions/{sid}').status_code,200)
        self.assertEqual(self.db.read_message(sid),[])
        self.assertIsNone(self.db.get_request('delete-test'))

    def test_deployed_cors(self):
        r=self.client.options('/sessions',headers={'Origin':'https://chatbot-db-front-x8gl.onrender.com','Access-Control-Request-Method':'POST'})
        self.assertEqual(r.headers['access-control-allow-origin'],'https://chatbot-db-front-x8gl.onrender.com')
        r=self.client.options('/sessions',headers={'Origin':'https://untrusted.example','Access-Control-Request-Method':'POST'})
        self.assertNotIn('access-control-allow-origin',r.headers)

    def test_credits_error_is_actionable(self):
        response=Mock(); response.status_code=402
        response.raise_for_status.side_effect=requests.HTTPError(response=response)
        with patch.object(self.main.requests,'post',return_value=response):
            r=self.client.post('/chat',json={'text':'안녕'})
        self.assertEqual(r.status_code,503)
        self.assertIn('크레딧',r.json()['detail'])

    def test_malformed_ai_response(self):
        response=Mock(); response.json.return_value={'choices':[]}
        with patch.object(self.main.requests,'post',return_value=response):
            self.assertEqual(self.client.post('/chat',json={'text':'안녕'}).status_code,502)

    def test_ai_prompt_and_timeout(self):
        response=Mock(); response.json.return_value={'choices':[{'message':{'content':'답변'}}]}
        with patch.object(self.main.requests,'post',return_value=response) as post:
            self.assertEqual(self.client.post('/chat',json={'text':'안녕'}).status_code,200)
            self.assertEqual(post.call_args.kwargs['json']['messages'][0]['role'],'system')
            self.assertEqual(post.call_args.kwargs['timeout'],(10,60))

    def test_busy_session(self):
        sid=self.session()
        lock=self.main._session_locks[sid % 128]
        lock.acquire()
        try:
            self.assertEqual(self.client.post(f'/sessions/{sid}/messages',json={'text':'중복'}).status_code,409)
        finally: lock.release()

if __name__ == '__main__': unittest.main()
