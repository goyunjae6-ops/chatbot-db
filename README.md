# 🤖 AI Chatbot

FastAPI와 React(Vite), 그리고 Hugging Face AI 모델(`Qwen/Qwen3-4B-Instruct-2507`)을 연동한 풀스택 AI 챗봇 웹 애플리케이션입니다.

---

## 🌐 배포 도메인 (Live Services)

현재 서비스는 **Render** 플랫폼을 통해 프론트엔드와 백엔드가 각각 분리 배포되어 운영 중입니다.

| 구분 | 서비스 | URL |
| :--- | :--- | :--- |
| **Frontend** | React 웹 클라이언트 (Static Site) | [https://two026-chatbot-frontend.onrender.com](https://two026-chatbot-frontend.onrender.com) |
| **Backend** | FastAPI 서버 (Web Service) | [https://two026-chatbot-backend.onrender.com](https://two026-chatbot-backend.onrender.com) |
| **API Docs** | Swagger UI (대화형 API 문서) | [https://two026-chatbot-backend.onrender.com/docs](https://two026-chatbot-backend.onrender.com/docs) |
| **Repository** | GitHub 저장소 | [https://github.com/goyunjae6-ops/ai-chatbot](https://github.com/goyunjae6-ops/ai-chatbot) |

---

## 🛠️ 기술 스택 (Tech Stack)

### Frontend
- **Framework / Tool**: React 19, Vite
- **Language**: JavaScript (ES Module)
- **Styling**: Vanilla CSS
- **Deployment**: Render Static Site

### Backend
- **Framework**: FastAPI, Uvicorn
- **Language**: Python 3.10+
- **Data Validation**: Pydantic
- **Environment Management**: Python-dotenv
- **Deployment**: Render Web Service

### AI Model
- **Platform**: Hugging Face Inference API (`router.huggingface.co`)
- **Model**: `Qwen/Qwen3-4B-Instruct-2507`

---

## 📁 프로젝트 구조 (Directory Structure)

```plaintext
chatbot/
├── backend/
│   ├── main.py              # FastAPI 서버 엔드포인트 및 Hugging Face API 연동
│   ├── requirements.txt     # 백엔드 의존성 패키지 목록
│   └── .env                 # Hugging Face 토큰 환경변수 (보안상 .gitignore 처리)
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # 채팅 인터페이스 UI 및 API 호출 로직
│   │   ├── main.jsx         # React 진입점
│   │   └── index.css        # 채팅창 스타일링
│   ├── index.html           # HTML 템플릿
│   ├── package.json         # 프론트엔드 의존성 및 실행 스크립트
│   └── vite.config.js       # Vite 설정 파일
└── README.md                # 프로젝트 문서
```

---

## 🚀 로컬 실행 가이드 (Local Development)

### 1. 사전 요구사항
- Node.js 18 이상
- Python 3.10 이상
- Hugging Face Access Token

### 2. 저장소 복제
```bash
git clone https://github.com/goyunjae6-ops/ai-chatbot.git
cd ai-chatbot
```

### 3. 백엔드 설정 및 실행
```bash
cd backend

# 가상환경 생성 및 활성화
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate

# 의존성 패키지 설치
pip install -r requirements.txt

# .env 파일 생성 후 토큰 설정
echo "HF_TOKEN=your_huggingface_token_here" > .env

# 백엔드 서버 시작 (기본 포트: 8000)
uvicorn main:app --reload
```

### 4. 프론트엔드 설정 및 실행
새 터미널을 열고 다음 명령어를 실행합니다:
```bash
cd frontend

# 패키지 설치
npm install

# 개발 서버 실행 (기본 포트: 5173)
npm run dev
```

브라우저에서 `http://localhost:5173`으로 접속하여 테스트합니다.

---

## 📡 API 명세서 (API Specification)

### `POST /chat`
사용자의 메시지를 전달받아 Hugging Face AI 모델의 답변을 반환합니다.

#### Request
- **URL**: `/chat`
- **Method**: `POST`
- **Headers**: `Content-Type: application/json`
- **Body**:
  ```json
  {
    "text": "안녕하세요!"
  }
  ```

#### Response
- **Status Code**: `200 OK`
- **Body**:
  ```json
  {
    "reply": "안녕하세요! 무엇을 도와드릴까요?"
  }
  ```

---

## 🚢 배포 설정 (Render Deployment)

### Backend (Web Service)
- **Root Directory**: `backend`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Environment Variables**:
  - `HF_TOKEN`: Hugging Face API User Access Token

### Frontend (Static Site)
- **Root Directory**: `frontend`
- **Build Command**: `npm run build`
- **Publish Directory**: `dist`
