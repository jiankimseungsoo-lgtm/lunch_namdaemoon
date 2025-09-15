// Gemini API 연동 모듈
class GeminiRecommendation {
    constructor(apiKey) {
        this.apiKey = apiKey;
        this.apiUrl = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent';
    }

    // AI 추천 요청 (사용자 프롬프트 기반)
    async getRecommendation(userPrompt, restaurantData) {
        try {
            if (!this.apiKey || this.apiKey.trim() === '') {
                throw new Error('API 키가 설정되지 않았습니다.');
            }

            if (!userPrompt || userPrompt.trim() === '') {
                throw new Error('추천 요청 내용을 입력해주세요.');
            }

            if (!restaurantData || restaurantData.length === 0) {
                throw new Error('추천할 맛집 데이터가 없습니다.');
            }

            const prompt = this.createPrompt(userPrompt, restaurantData);

            console.log('Gemini API 요청 시작:', {
                apiUrl: this.apiUrl,
                promptLength: prompt.length,
                restaurantCount: restaurantData.length
            });

            const response = await fetch(`${this.apiUrl}?key=${this.apiKey}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    contents: [{
                        parts: [{
                            text: prompt
                        }]
                    }],
                    generationConfig: {
                        temperature: 0.7,
                        topK: 40,
                        topP: 0.95,
                        maxOutputTokens: 1024
                    }
                })
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error('Gemini API 에러 응답:', errorText);
                throw new Error(`Gemini API 오류 (${response.status}): ${errorText}`);
            }

            const data = await response.json();
            console.log('Gemini API 응답:', data);

            if (!data.candidates || data.candidates.length === 0) {
                throw new Error('AI가 응답을 생성하지 못했습니다.');
            }

            const aiResponse = data.candidates[0].content.parts[0].text;
            console.log('AI 응답 텍스트:', aiResponse);

            return this.parseRecommendation(aiResponse, restaurantData);

        } catch (error) {
            console.error('AI 추천 실패:', error);
            throw error;
        }
    }

    // 프롬프트 생성 (사용자 자유 입력 기반)
    createPrompt(userRequest, restaurants) {
        // 레스토랑 리스트를 더 자세하고 읽기 쉽게 포맷팅
        const restaurantList = restaurants.map((r, index) => {
            const walkingTime = r.walking_time_min ? `${r.walking_time_min}분` : '미정';
            const distance = r.distance_from_office_m ? `${r.distance_from_office_m}m` : '미정';
            const rating = r.rating ? `${r.rating}/5.0` : '미정';
            const menu = r.signature_menu || '정보 없음';

            return `${index + 1}. 【${r.name}】
   - 장르: ${r.food_genre}
   - 거리: ${distance} (도보 ${walkingTime})
   - 평점: ${rating}
   - 대표메뉴: ${menu}`;
        }).join('\n\n');

        return `당신은 서울 남대문/중구 일대의 점심 맛집 추천 전문가입니다.
그레이츠숙례에서 일하는 직장인에게 최적의 점심 맛집을 추천해주세요.

👤 사용자의 요청:
"${userRequest}"

🍽️ 추천 가능한 맛집 목록 (그레이츠숙례 기준):
${restaurantList}

📋 추천 기준:
1. 사용자 요청과의 적합성 (음식 종류, 분위기, 특별한 상황 등)
2. 맛집의 평점과 품질
3. 그레이츠숙례에서의 접근성 (거리, 도보시간)
4. 점심시간 이용 편의성

⚠️ 중요: 반드시 위 목록에 있는 맛집 중에서만 추천해주세요.

📝 응답 형식 (정확히 이 형식을 따라주세요):
RECOMMENDATION: [번호]
REASON: [사용자 요청을 바탕으로 한 추천 이유 2-3줄]
TIPS: [방문 팁이나 추천 메뉴]

📖 응답 예시:
RECOMMENDATION: 3
REASON: 사용자가 따뜻한 국물 요리를 원하셨는데, 이 곳의 한우곰탕이 완벽합니다. 평점 4.2점으로 높고 도보 7분으로 접근성도 좋습니다.
TIPS: 점심시간 12시 이전 방문 추천드리며, 곰탕에 김치를 곁들이면 더욱 맛있습니다.`;
    }

    // AI 응답 파싱
    parseRecommendation(aiResponse, restaurants) {
        try {
            console.log('AI 응답 파싱 시작:', aiResponse);

            const lines = aiResponse.split('\n').map(line => line.trim());
            let recommendationIndex = null;
            let reason = '';
            let tips = '';
            let currentSection = '';

            for (const line of lines) {
                if (line.includes('RECOMMENDATION:')) {
                    // 숫자 추출을 더 유연하게
                    const match = line.match(/RECOMMENDATION:\s*(\d+)/i);
                    if (match) {
                        recommendationIndex = parseInt(match[1]) - 1; // 0-based index
                        console.log('추천 번호 파싱:', match[1], '-> 인덱스:', recommendationIndex);
                    }
                    currentSection = 'recommendation';
                } else if (line.includes('REASON:')) {
                    reason = line.replace(/REASON:/i, '').trim();
                    currentSection = 'reason';
                } else if (line.includes('TIPS:')) {
                    tips = line.replace(/TIPS:/i, '').trim();
                    currentSection = 'tips';
                } else if (line && currentSection === 'reason' && !line.includes('TIPS:')) {
                    // 이유가 여러 줄인 경우
                    reason += (reason ? ' ' : '') + line;
                } else if (line && currentSection === 'tips') {
                    // 팁이 여러 줄인 경우
                    tips += (tips ? ' ' : '') + line;
                }
            }

            console.log('파싱 결과:', {
                recommendationIndex,
                reason,
                tips,
                validIndex: recommendationIndex >= 0 && recommendationIndex < restaurants.length
            });

            // 유효한 추천인지 확인
            if (recommendationIndex !== null && recommendationIndex >= 0 && recommendationIndex < restaurants.length) {
                return {
                    restaurant: restaurants[recommendationIndex],
                    reason: reason || 'AI가 이 맛집을 추천했습니다.',
                    tips: tips || '맛있게 드세요!',
                    isAiRecommendation: true
                };
            } else {
                console.warn('유효하지 않은 추천 번호, 첫 번째 맛집으로 대체');
                return {
                    restaurant: restaurants[0],
                    reason: reason || 'AI 추천 번호를 찾을 수 없어 대표 맛집을 추천드립니다.',
                    tips: tips || '맛있게 드세요!',
                    isAiRecommendation: false
                };
            }
        } catch (error) {
            console.error('AI 응답 파싱 오류:', error);
            return {
                restaurant: restaurants[0],
                reason: 'AI 추천 처리 중 오류가 발생했습니다.',
                tips: '맛있게 드세요!',
                isAiRecommendation: false
            };
        }
    }

    // 사용자 선호도 기반 맛집 필터링
    filterRestaurantsByPreferences(restaurants, preferences) {
        let filtered = [...restaurants];

        // 음식 종류 필터
        if (preferences.foodType && preferences.foodType !== '상관없음') {
            filtered = filtered.filter(r => r.food_genre === preferences.foodType);
        }

        // 거리 필터
        if (preferences.distance) {
            const maxMinutes = parseInt(preferences.distance);
            if (!isNaN(maxMinutes)) {
                filtered = filtered.filter(r => (r.walking_time_min || 999) <= maxMinutes);
            }
        }

        // 평점 필터 (예산에 따라)
        if (preferences.budget === '고급') {
            filtered = filtered.filter(r => (r.rating || 0) >= 4.0);
        } else if (preferences.budget === '저렴') {
            filtered = filtered.filter(r => (r.rating || 0) >= 3.5);
        }

        // 최소 10개는 유지
        if (filtered.length < 10 && restaurants.length >= 10) {
            filtered = restaurants.slice(0, 20);
        }

        return filtered;
    }
}

// API 키 관리
class ApiKeyManager {
    static getStoredApiKey() {
        return localStorage.getItem('gemini_api_key');
    }

    static setApiKey(apiKey) {
        localStorage.setItem('gemini_api_key', apiKey);
    }

    static clearApiKey() {
        localStorage.removeItem('gemini_api_key');
    }

    static isValidApiKey(apiKey) {
        return apiKey && apiKey.length > 20 && apiKey.startsWith('AIza');
    }
}

// 전역으로 사용할 수 있도록 export
window.GeminiRecommendation = GeminiRecommendation;
window.ApiKeyManager = ApiKeyManager;