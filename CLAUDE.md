# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Korean restaurant recommendation web application called "점심 맛집 추천기" (Lunch Restaurant Recommender) for employees of "그레이츠숙례" company. The app recommends restaurants in the Seoul Namdaemun/Jung-gu area with two main features:

1. **Random Recommendation**: Filter-based random restaurant selection
2. **AI-Powered Recommendation**: Google Gemini AI integration for natural language-based personalized recommendations

## Architecture

### Frontend Stack
- **Pure HTML/CSS/JavaScript**: No frameworks, vanilla JS approach
- **Static Data**: Restaurant data stored in JSONL format
- **Responsive Design**: Mobile-first design with minimal color palette

### Key Components
- `index.html`: Main application entry point with filters and recommendation UI
- `script.js`: Core application logic including data loading, filtering, and random recommendations
- `gemini-api.js`: Google Gemini AI integration module with `GeminiRecommendation` class
- `config.js`: API configuration (contains Gemini API key)
- `style.css` + `modern_styles.css`: Styling with minimal design approach

### Data Architecture
- `unified_restaurant_datamart.jsonl`: Restaurant data in JSONL format (20 curated restaurants)
- Each restaurant includes: name, genre, rating, distance from office, walking time, signature menu, Naver map link
- Data structure: `{restaurant_id, name, food_genre, rating, distance_from_office_m, walking_time_min, signature_menu, naver_map_link, data_quality_score}`

### Data Collection
- `diningcode_playwright_scraper.py`: Python script using Playwright for web scraping restaurant data from DiningCode
- Collects data from Seoul Station, Namdaemun, and Hoehyeon Station areas

## Development Commands

### Local Development
```bash
# Serve the application locally (Windows)
python -m http.server 8000

# Access at http://localhost:8000
```

### Data Collection and Scraping
```bash
# Set up Python environment (if needed)
python -m venv .venv
.venv\Scripts\activate  # Windows

# Install Python dependencies
pip install playwright tqdm

# Install browser binaries
playwright install

# Run the scraper (collected 720 restaurants, deduplicated to 20)
python diningcode_playwright_scraper.py
```

### Testing and Debugging
```bash
# Open browser console to debug JavaScript
# Check for errors in browser DevTools (F12)

# Test data loading locally
python -m http.server 8000
# Navigate to http://localhost:8000 and check console logs

# Validate JSONL data format
python -c "import json; [json.loads(line) for line in open('unified_restaurant_datamart.jsonl')]"
```

### Deployment
The application is configured for Vercel deployment with GitHub Actions:
```bash
# Using Vercel CLI (alternative method)
vercel login
vercel
vercel --prod
```

**Automatic Deployment**: GitHub Actions workflow automatically deploys on push to master/main branches using `.github/workflows/deploy.yml`.

## Key Features Implementation

### Filtering System
- **Genre Filter**: Buttons for Korean, Chinese, Japanese, Western, Snacks, Cafe, etc.
- **Distance Filter**: Slider (100m-1000m) with real-time restaurant count updates
- Real-time filtering updates the available restaurant pool for recommendations

### AI Recommendation Flow
1. User inputs natural language request (e.g., "I want warm soup dishes")
2. `GeminiRecommendation.getRecommendation()` processes request with current filtered restaurants
3. AI returns structured response: `RECOMMENDATION: [number]`, `REASON: [explanation]`, `TIPS: [advice]`
4. Application parses response and displays recommended restaurant with AI reasoning

### Module Dependencies and Loading Order
1. `config.js` - Must load first (contains API keys)
2. `gemini-api.js` - Depends on `window.API_CONFIG` from config.js
3. `script.js` - Main application, depends on `GeminiRecommendation` class
4. Data loading happens asynchronously via fetch in `script.js`

### Restaurant Data Structure
Each restaurant object contains:
- Basic info: name, food_genre, rating, review_count
- Location data: distance_from_office_m, walking_time_min, location_description
- Links: naver_map_link, url (to source data)
- Metadata: data_source, data_quality_score, restaurant_id

## Important Implementation Details

### API Key Management
- Gemini API key stored in `config.js` and exposed globally via `window.API_CONFIG`
- `ApiKeyManager` class provides localStorage-based key management functions
- API key validation checks for format starting with "AIza"

### Error Handling
- Comprehensive error handling for data loading failures
- AI API failures fall back to first restaurant with error message
- Invalid AI responses default to first restaurant in filtered list

### Responsive Design
- Mobile-optimized layout with card-based design
- Minimal color scheme focusing on usability
- Smooth animations and hover effects

## File Organization
```
/
├── index.html              # Main application
├── script.js              # Core application logic
├── gemini-api.js          # AI integration
├── config.js              # API configuration
├── style.css              # Main styles
├── modern_styles.css      # Additional modern styling
├── unified_restaurant_datamart.jsonl  # Restaurant data
├── diningcode_playwright_scraper.py   # Data collection script
├── README.md              # Project documentation
├── DEPLOYMENT.md          # Deployment guide
└── .github/workflows/deploy.yml       # CI/CD pipeline
```

## Development Notes

- **No package.json** - this is a vanilla JavaScript project with no npm dependencies
- **No build process** - serves static files directly via HTTP server
- **No lint/test commands** - manual testing via browser
- **API key committed** - Gemini API key stored in `config.js` (development project)
- **Restaurant data manually curated** - 720 scraped restaurants deduplicated to 20 high-quality entries
- **Korean UI** - all text in Korean for the target audience (Korean office workers)
- **Windows development environment** - file paths and commands optimized for Windows

## Project State Management

### Core Application Flow
1. **Data Loading**: `script.js` loads JSONL data via fetch on DOM ready
2. **Filter Management**: Real-time filtering updates `filteredRestaurants` array
3. **Random Recommendation**: Selects random restaurant from filtered pool
4. **AI Recommendation**: Passes filtered restaurants to Gemini API via `gemini-api.js`
5. **Result Display**: Updates DOM with restaurant cards and AI reasoning

### State Variables (script.js)
- `allRestaurants`: Complete dataset loaded from JSONL
- `filteredRestaurants`: Current filtered subset based on genre/distance
- `selectedGenre`: Current genre filter ('all', '한식', '중식', etc.)
- `maxDistance`: Current distance filter in meters (100-1000m)
- `geminiAI`: Instance of `GeminiRecommendation` class

### Error Handling Strategy
- **Data loading failures**: Display error card with reload option
- **AI API failures**: Fall back to first restaurant in filtered list
- **Invalid AI responses**: Parse failure defaults to first restaurant
- **Empty filter results**: Show "no restaurants" message

## Common Development Tasks

### Updating Restaurant Data
1. Modify `unified_restaurant_datamart.jsonl` directly or re-run scraper
2. Validate JSON format: `python -c "import json; [json.loads(line) for line in open('unified_restaurant_datamart.jsonl')]"`
3. Test locally with `python -m http.server 8000`

### Modifying AI Responses
- Edit prompt templates in `gemini-api.js` → `createPrompt()` method
- Adjust response parsing in `gemini-api.js` → `parseAIResponse()` method
- Update response format expectations in `script.js` → AI recommendation handlers

### Adding New Filters
1. Add UI elements in `index.html`
2. Update filter logic in `script.js` → `applyFilters()` function
3. Update stats display in `updateStats()` function

### Debugging Common Issues
- **Data not loading**: Check browser console, verify JSONL format
- **AI not responding**: Verify API key in `config.js`, check network requests
- **Filters not working**: Check `filteredRestaurants` array in console
- **Styling issues**: Check CSS conflicts between `style.css` and `modern_styles.css`

## 클로드 코드에서의 mcp-installer를 사용한 MCP (Model Context Protocol) 설치 및 설정 가이드

### 공통 주의사항
1. 현재 사용 환경을 확인할 것. 모르면 사용자에게 물어볼 것.
2. OS(윈도우,리눅스,맥) 및 환경들(WSL,파워셀,명령프롬프트등)을 파악해서 그에 맞게 세팅할 것. 모르면 사용자에게 물어볼 것.
3. mcp-installer을 이용해 필요한 MCP들을 설치할 것
   (user 스코프로 설치 및 적용할것)
4. 특정 MCP 설치시, 바로 설치하지 말고, WebSearch 도구로 해당 MCP의 공식 사이트 확인하고 현재 OS 및 환경 매치하여, 공식 설치법부터 확인할 것
5. 공식 사이트 확인 후에는 context7 MCP 존재하는 경우, context7으로 다시 한번 확인할 것
6. MCP 설치 후, task를 통해 디버그 모드로 서브 에이전트 구동한 후, /mcp 를 통해 실제 작동여부를 반드시 확인할 것
7. 설정 시, API KEY 환경 변수 설정이 필요한 경우, 가상의 API 키로 디폴트로 설치 및 설정 후, 올바른 API 키 정보를 입력해야 함을 사용자에게 알릴 것
8. Mysql MCP와 같이 특정 서버가 구동중 상태여만 정상 작동한 것은 에러가 나도 재설치하지 말고, 정상 구동을 위한 조건을 사용자에게 알릴 것
9. 현재 클로드 코드가 실행되는 환경이야.
10. 설치 요청 받은 MCP만 설치하면 돼. 혹시 이미 설치된 다른 MCP 에러 있어도, 그냥 둘 것
11. 일단, 터미널에서 설치하려는 MCP 작동 성공한 경우, 성공 시의 인자 및 환경 변수 이름을 활용해, 올바른 위치의 json 파일에 MCP 설정을 직접할 것
12. WSL sudo 패스워드: qsc1445! (WSL 환경인 경우에만 해당)

### 윈도우에서의 주의사항
1. 설정 파일 직접 세팅시, Windows 경로 구분자는 백슬래시(\)이며, JSON 내에서는 반드시 이스케이프 처리(\\\\)해야 해.

### OS 공통 주의사항
1. Node.js가 %PATH%에 등록되어 있는지, 버전이 최소 v18 이상인지 확인할 것
2. npx -y 옵션을 추가하면 버전 호환성 문제를 줄일 수 있음

### MCP 서버 설치 순서

#### 1. 기본 설치
mcp-installer를 사용해 설치할 것

#### 2. 설치 후 정상 설치 여부 확인하기
claude mcp list 으로 설치 목록에 포함되는지 내용 확인한 후,
task를 통해 디버그 모드로 서브 에이전트 구동한 후 (claude --debug), 최대 2분 동안 관찰한 후, 그 동안의 디버그 메시지(에러 시 관련 내용이 출력됨)를 확인하고 /mcp 를 통해(Bash(echo "/mcp" | claude --debug)) 실제 작동여부를 반드시 확인할 것

#### 3. 문제 있을때 다음을 통해 직접 설치할 것

User 스코프로 claude mcp add 명령어를 통한 설정 파일 세팅 예시
예시1:
```bash
claude mcp add --scope user youtube-mcp \
  -e YOUTUBE_API_KEY=$YOUR_YT_API_KEY \
  -e YOUTUBE_TRANSCRIPT_LANG=ko \
  -- npx -y youtube-data-mcp-server
```

#### 4. 정상 설치 여부 확인 하기
claude mcp list 으로 설치 목록에 포함되는지 내용 확인한 후,
task를 통해 디버그 모드로 서브 에이전트 구동한 후 (claude --debug), 최대 2분 동안 관찰한 후, 그 동안의 디버그 메시지(에러 시 관련 내용이 출력됨)를 확인하고, /mcp 를 통해(Bash(echo "/mcp" | claude --debug)) 실제 작동여부를 반드시 확인할 것

#### 5. 문제 있을때 공식 사이트 다시 확인후 권장되는 방법으로 설치 및 설정할 것
(npm/npx 패키지를 찾을 수 없는 경우) npm 전역 설치 경로 확인 : npm config get prefix
권장되는 방법을 확인한 후, npm, pip, uvx, pip 등으로 직접 설치할 것

##### uvx 명령어를 찾을 수 없는 경우
```bash
# uv 설치 (Python 패키지 관리자)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

##### npm/npx 패키지를 찾을 수 없는 경우
```bash
# npm 전역 설치 경로 확인
npm config get prefix
```

### 설치 후 터미널 상에서 작동 여부 점검할 것

### 위 방법으로, 터미널에서 작동 성공한 경우, 성공 시의 인자 및 환경 변수 이름을 활용해서, 클로드 코드의 올바른 위치의 json 설정 파일에 MCP를 직접 설정할 것

#### 설정 예시
(설정 파일 위치)
**리눅스, macOS 또는 윈도우 WSL 기반의 클로드 코드인 경우**
- **User 설정**: `~/.claude/` 디렉토리
- **Project 설정**: 프로젝트 루트/.claude

**윈도우 네이티브 클로드 코드인 경우**
- **User 설정**: `C:\Users\{사용자명}\.claude` 디렉토리
- User 설정파일  C:\Users\{사용자명}\.claude.json
- **Project 설정**: 프로젝트 루트\.claude

##### 1. npx 사용
```json
{
  "youtube-mcp": {
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "youtube-data-mcp-server"],
    "env": {
      "YOUTUBE_API_KEY": "YOUR_API_KEY_HERE",
      "YOUTUBE_TRANSCRIPT_LANG": "ko"
    }
  }
}
```

##### 2. cmd.exe 래퍼 + 자동 동의
```json
{
  "mcpServers": {
    "mcp-installer": {
      "command": "cmd.exe",
      "args": ["/c", "npx", "-y", "@anaisbetts/mcp-installer"],
      "type": "stdio"
    }
  }
}
```

##### 3. 파워셀예시
```json
{
  "command": "powershell.exe",
  "args": [
    "-NoLogo", "-NoProfile",
    "-Command", "npx -y @anaisbetts/mcp-installer"
  ]
}
```

##### 4. npx 대신 node 지정
```json
{
  "command": "node",
  "args": [
    "%APPDATA%\\npm\\node_modules\\@anaisbetts\\mcp-installer\\dist\\index.js"
  ]
}
```

##### 5. args 배열 설계 시 체크리스트
- 토큰 단위 분리: "args": ["/c","npx","-y","pkg"] 와 "args": ["/c","npx -y pkg"] 는 동일해보여도 cmd.exe 내부에서 따옴표 처리 방식이 달라질 수 있음. 분리가 안전.
- 경로 포함 시: JSON에서는 \\\\ 두 번. 예) "C:\\\\tools\\\\mcp\\\\server.js".
- 환경변수 전달: "env": { "UV_DEPS_CACHE": "%TEMP%\\\\uvcache" }
- 타임아웃 조정: 느린 PC라면 MCP_TIMEOUT 환경변수로 부팅 최대 시간을 늘릴 수 있음 (예: 10000 = 10 초)

### 중요사항
윈도우 네이티브 환경이고 MCP 설정에 어려움이 있는데 npx 환경이라면, cmd나 node 등으로 다음과 같이 대체해 볼것:
```json
{
  "mcpServers": {
    "context7": {
      "command": "cmd",
      "args": ["/c", "npx", "-y", "@upstash/context7-mcp@latest"]
    }
  }
}
```

```bash
claude mcp add-json context7 -s user '{"type":"stdio","command":"cmd","args": ["/c", "npx", "-y", "@upstash/context7-mcp@latest"]}'
```