# 🚀 Vercel 배포 가이드

## 방법 1: Vercel 웹 인터페이스 (추천)

### 1단계: Vercel 계정 생성 및 로그인
1. [vercel.com](https://vercel.com) 접속
2. GitHub 계정으로 로그인

### 2단계: 새 프로젝트 생성
1. **"New Project"** 버튼 클릭
2. **GitHub 리포지토리 연결**
3. `jiankimseungsoo-lgtm/lunch_namdaemoon` 선택
4. **"Import"** 클릭

### 3단계: 프로젝트 설정
```
Framework Preset: Other
Root Directory: ./
Build Command: (비워둠 - 정적 사이트)
Output Directory: ./
Install Command: (비워둠)
```

### 4단계: 환경 변수 설정 (선택사항)
Environment Variables에서 설정:
```
GEMINI_API_KEY = your_actual_api_key_here
```

### 5단계: 배포 실행
1. **"Deploy"** 버튼 클릭
2. 자동 빌드 및 배포 진행
3. 완료되면 배포 URL 제공

---

## 방법 2: Vercel CLI (고급 사용자)

### 1단계: CLI 로그인
```bash
vercel login
```

### 2단계: 프로젝트 배포
```bash
vercel
```

### 3단계: 프로덕션 배포
```bash
vercel --prod
```

---

## 🔧 배포 후 확인사항

### 1. 기본 기능 테스트
- [ ] 페이지 로딩 정상
- [ ] Jian 로고 표시
- [ ] 랜덤 추천 버튼 동작
- [ ] 필터링 기능 동작

### 2. AI 추천 기능 테스트
- [ ] 프롬프트 입력란 표시
- [ ] AI 추천 버튼 클릭
- [ ] API 키 설정 확인
- [ ] 추천 결과 표시

### 3. 반응형 디자인 확인
- [ ] 모바일 레이아웃
- [ ] 태블릿 레이아웃
- [ ] 데스크톱 레이아웃

---

## 🚨 문제 해결

### API 키 관련 문제
1. `config.js`에서 API 키 확인
2. Vercel 환경변수 설정
3. `test_gemini.html`로 API 테스트

### 데이터 로딩 문제
1. `unified_restaurant_datamart.jsonl` 파일 확인
2. CORS 정책 문제 확인
3. 브라우저 개발자 도구에서 네트워크 탭 확인

### 스타일 문제
1. CSS 파일 로딩 확인
2. 브라우저 캐시 삭제
3. 모바일 뷰포트 메타태그 확인

---

## 📱 예상 배포 URL

배포 후 다음과 같은 URL이 생성됩니다:
- **Production**: https://lunch-namdaemoon.vercel.app
- **Preview**: https://lunch-namdaemoon-git-master-jiankimseungsoo-lgtm.vercel.app

---

## 🔄 자동 배포 설정

GitHub 연결 후 자동으로 다음이 설정됩니다:
- **main/master 브랜치**: 프로덕션 배포
- **다른 브랜치**: 프리뷰 배포
- **Pull Request**: 프리뷰 배포

매번 GitHub에 푸시할 때마다 자동으로 재배포됩니다!