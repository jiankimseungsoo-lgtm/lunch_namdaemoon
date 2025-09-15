# 🍽️ 점심 맛집 추천기

그레이츠숙례 직장인을 위한 스마트 점심 맛집 추천 서비스

## ✨ 주요 기능

- 🎲 **랜덤 추천**: 필터 조건에 맞는 맛집 랜덤 선택
- 🤖 **AI 맞춤 추천**: Google Gemini AI를 활용한 자연어 기반 맞춤 추천
- 🔍 **스마트 필터링**: 장르별, 거리별 맛집 필터링
- 📍 **위치 기반**: 그레이츠숙례 기준 도보 거리 및 시간 제공
- 📱 **반응형 디자인**: 모바일/데스크톱 최적화

## 🎨 디자인 특징

- **미니멀 디자인**: 색상을 최소화한 세련된 UI
- **Jian 로고**: 브랜드 아이덴티티 적용
- **카드 기반 레이아웃**: 직관적인 정보 구성
- **부드러운 애니메이션**: 자연스러운 사용자 경험

## 🚀 기술 스택

### Frontend
- **HTML5**: 시멘틱 마크업
- **CSS3**: 미니멀 디자인, 반응형 레이아웃
- **JavaScript (ES6+)**: 모던 자바스크립트

### Backend/API
- **Google Gemini AI**: AI 맛집 추천
- **Static JSON**: 통합 데이터 마트

### Data
- **통합 데이터 마트**: 중복 제거된 20개 고품질 맛집 정보
- **위치 정보**: 좌표, 거리, 도보 시간
- **평점 시스템**: 사용자 리뷰 기반 평점

## 📊 데이터 구조

```json
{
  "restaurant_id": "REST_0001_애성회관한우곰탕",
  "name": "애성회관 한우곰탕",
  "food_genre": "한식",
  "rating": 4.7,
  "distance_from_office_m": 547,
  "walking_time_min": 7,
  "signature_menu": "불고기",
  "naver_map_link": "https://map.naver.com/...",
  "data_quality_score": 100
}
```

## 🏗️ 프로젝트 구조

```
lunch_namdaemoon/
├── index.html                          # 메인 페이지
├── style.css                          # 미니멀 디자인 스타일
├── script.js                          # 메인 JavaScript 로직
├── gemini-api.js                      # AI 추천 API 연동
├── config.js                          # API 설정
├── unified_restaurant_datamart.jsonl  # 통합 맛집 데이터
├── datamart_metadata.json            # 데이터 메타정보
├── Jian.png                           # 브랜드 로고
└── README.md                          # 프로젝트 문서
```

## 🎯 사용 방법

### 1. 랜덤 추천
1. 원하는 장르/거리 필터 선택
2. "🎲 랜덤 추천" 버튼 클릭
3. 조건에 맞는 맛집 랜덤 표시

### 2. AI 맞춤 추천
1. "🤖 AI 맞춤 추천" 버튼 클릭
2. 자연어로 원하는 조건 입력
   - 예: "따뜻한 국물 요리가 먹고 싶어"
   - 예: "데이트하기 좋은 분위기 있는 곳"
3. AI가 분석하여 최적의 맛집 추천

## 🏃‍♂️ 로컬 실행

```bash
# 1. 리포지토리 클론
git clone https://github.com/jiankimseungsoo-lgtm/lunch_namdaemoon.git

# 2. 디렉토리 이동
cd lunch_namdaemoon

# 3. 로컬 서버 실행
python -m http.server 8000

# 4. 브라우저에서 접속
# http://localhost:8000
```

## 🌐 배포

- **Vercel**: [배포 URL 추가 예정]
- **GitHub Pages**: [배포 URL 추가 예정]

## 📈 데이터 통계

- **총 맛집 수**: 20개 (중복 제거)
- **데이터 품질**: 100% Excellent
- **장르 분포**:
  - 한식: 11개 (55%)
  - 기타: 6개 (30%)
  - 중식: 1개 (5%)
  - 카페/디저트: 1개 (5%)
  - 분식/간식: 1개 (5%)

## 🔧 개발 과정

1. **데이터 수집**: 다이닝코드 기반 맛집 정보
2. **데이터 통합**: 720개 → 20개 중복 제거
3. **위치 정보 추가**: 그레이츠숙례 기준 거리 계산
4. **AI 연동**: Google Gemini API 통합
5. **UI/UX 개선**: 미니멀 디자인 적용

## 📝 라이선스

MIT License

## 👨‍💻 개발자

**Jian Kim**
- GitHub: [@jiankimseungsoo-lgtm](https://github.com/jiankimseungsoo-lgtm)
- 그레이츠숙례 기준 맛집 큐레이션 시스템

---

**Made with ❤️ for 그레이츠숙례 직장인들**