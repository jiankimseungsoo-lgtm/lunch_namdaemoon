document.addEventListener('DOMContentLoaded', () => {
    const pickButton = document.getElementById('pick-button');
    const resultCard = document.getElementById('result-card');
    const totalCountElement = document.getElementById('total-count');
    const filteredCountElement = document.getElementById('filtered-count');
    
    let allRestaurants = [];
    let filteredRestaurants = [];
    let selectedGenre = 'all';
    let selectedDistance = 'all';
    let geminiAI = null;

    // 1. JSONL 데이터 로드 및 파싱
    async function loadData() {
        try {
            resultCard.innerHTML = '<p class="loading">맛집 데이터를 불러오는 중...</p>';
            
            const response = await fetch('./unified_restaurant_datamart.jsonl');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const text = await response.text();
            
            // JSONL 파싱: 각 줄이 하나의 JSON 객체
            allRestaurants = text.trim().split('\n')
                                .filter(line => line.trim() !== '')
                                .map(line => JSON.parse(line));
            
            filteredRestaurants = [...allRestaurants];
            
            console.log(`데이터 로드 완료: ${allRestaurants.length}개 맛집`);
            
            // 통계 업데이트
            updateStats();
            
            // 초기 메시지
            showWelcomeMessage();
            
            // 필터 이벤트 리스너 설정
            setupFilterEventListeners();
            
            // AI 기능 초기화
            initializeAI();
            
        } catch (error) {
            console.error('데이터 로드 실패:', error);
            resultCard.innerHTML = `
                <div class="error">
                    <p><strong>⚠️ 오류</strong></p>
                    <p>맛집 데이터를 불러올 수 없습니다.</p>
                    <p style="font-size: 0.8rem;">restaurants_with_coordinates.jsonl 파일을 확인해주세요.</p>
                </div>
            `;
        }
    }

    // 2. 환영 메시지 표시
    function showWelcomeMessage() {
        resultCard.innerHTML = `
            <p>🏢 <strong>그레이츠숙례</strong>에서 출발</p>
            <p>필터를 선택하고 버튼을 눌러 맛집을 추천받아보세요!</p>
            <p style="font-size: 0.9rem; color: #888; margin-top: 1rem;">
                📍 총 ${allRestaurants.length}개의 남대문 일대 맛집<br>
                🚶‍♂️ 평균 거리: ${calculateAverageDistance()}m<br>
                ⭐ 평균 평점: ${calculateAverageRating()}/5.0
            </p>
        `;
    }

    // 3. 통계 계산 함수들
    function calculateAverageDistance() {
        const validDistances = allRestaurants
            .map(r => r.distance_from_office_m)
            .filter(d => d && d > 0);
        
        if (validDistances.length === 0) return 0;
        
        const average = validDistances.reduce((sum, d) => sum + d, 0) / validDistances.length;
        return Math.round(average);
    }

    function calculateAverageRating() {
        const validRatings = allRestaurants
            .map(r => r.rating)
            .filter(r => r && r > 0);
        
        if (validRatings.length === 0) return 0;
        
        const average = validRatings.reduce((sum, r) => sum + r, 0) / validRatings.length;
        return average.toFixed(1);
    }

    // 4. 통계 업데이트
    function updateStats() {
        totalCountElement.textContent = allRestaurants.length;
        filteredCountElement.textContent = filteredRestaurants.length;
    }

    // 5. 필터링 함수
    function applyFilters() {
        filteredRestaurants = allRestaurants.filter(restaurant => {
            // 장르 필터
            const genreMatch = selectedGenre === 'all' || 
                              restaurant.food_genre === selectedGenre;
            
            // 거리 필터
            let distanceMatch = true;
            if (selectedDistance !== 'all') {
                const walkingTime = restaurant.walking_time_min || 999;
                distanceMatch = walkingTime <= parseInt(selectedDistance);
            }
            
            return genreMatch && distanceMatch;
        });
        
        updateStats();
        console.log(`필터링 결과: ${filteredRestaurants.length}개 맛집`);
    }

    // 6. 필터 이벤트 리스너 설정
    function setupFilterEventListeners() {
        // 장르 필터 버튼들
        const genreButtons = document.querySelectorAll('.genre-btn');
        genreButtons.forEach(button => {
            button.addEventListener('click', () => {
                genreButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');
                selectedGenre = button.dataset.genre;
                applyFilters();
            });
        });

        // 거리 필터 버튼들
        const distanceButtons = document.querySelectorAll('.distance-btn');
        distanceButtons.forEach(button => {
            button.addEventListener('click', () => {
                distanceButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');
                selectedDistance = button.dataset.distance;
                applyFilters();
            });
        });
    }

    // 7. 별점 표시 함수
    function generateStars(rating) {
        const fullStars = Math.floor(rating);
        const hasHalfStar = rating % 1 >= 0.5;
        const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);
        
        let stars = '★'.repeat(fullStars);
        if (hasHalfStar) stars += '☆';
        stars += '☆'.repeat(emptyStars);
        
        return stars;
    }

    // 8. 결과 렌더링 함수
    function renderResult(restaurant) {
        // 카드에 애니메이션 효과 추가
        resultCard.classList.add('active');
        
        const walkingTimeText = restaurant.walking_time_min ? 
            `${restaurant.walking_time_min}분` : '정보없음';
        
        const distanceText = restaurant.distance_from_office_m ? 
            `${restaurant.distance_from_office_m}m` : '정보없음';

        const rating = restaurant.rating || 0;
        const reviewCount = restaurant.review_count || 0;
        const stars = generateStars(rating);
        const signatureMenu = restaurant.signature_menu || '추천메뉴';

        resultCard.innerHTML = `
            ${restaurant.image_url ? `
                <img src="${restaurant.image_url}" alt="${restaurant.name}" class="restaurant-image" 
                     onerror="this.style.display='none'">
            ` : ''}
            
            <h2>🍽️ ${restaurant.name}</h2>
            <div class="genre">${restaurant.food_genre || '기타'}</div>
            <div class="signature-menu">🏆 ${signatureMenu}</div>
            
            <div class="rating-section">
                <span class="rating-stars">${stars}</span>
                <span class="rating-text">${rating}/5.0 (${reviewCount}개 리뷰)</span>
            </div>
            
            <p><strong>🏢 그레이츠숙례에서:</strong></p>
            <p class="distance"><strong>🚶‍♂️ ${distanceText} (도보 ${walkingTimeText})</strong></p>
            <p><strong>🎯 거리감:</strong> ${restaurant.distance_category || '보통'}</p>
            <p><strong>📍 위치:</strong> ${restaurant.location_description || '남대문/중구 일대'}</p>
            
            ${restaurant.naver_map_link ? `
                <div class="naver-link">
                    <a href="${restaurant.naver_map_link}" target="_blank" rel="noopener">
                        🗺️ 네이버 지도에서 보기
                    </a>
                </div>
            ` : ''}
        `;
    }

    // 9. 버튼 클릭 이벤트 리스너
    pickButton.addEventListener('click', () => {
        if (filteredRestaurants.length === 0) {
            resultCard.innerHTML = `
                <div class="error">
                    <p>선택한 조건에 맞는 맛집이 없습니다!</p>
                    <p style="font-size: 0.9rem;">필터 조건을 다시 선택해보세요.</p>
                </div>
            `;
            return;
        }

        // 버튼 애니메이션
        pickButton.style.transform = 'scale(0.95)';
        setTimeout(() => {
            pickButton.style.transform = 'scale(1)';
        }, 100);

        // 랜덤 선택
        const randomIndex = Math.floor(Math.random() * filteredRestaurants.length);
        const randomPick = filteredRestaurants[randomIndex];
        
        // 결과 렌더링
        renderResult(randomPick);
        
        console.log('선택된 맛집:', randomPick);
    });

    // 10. 추가 기능: 통계 보기
    window.showDetailedStats = function() {
        if (allRestaurants.length === 0) return;

        const genreCount = {};
        const distanceCount = {};
        const ratingDistribution = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
        
        allRestaurants.forEach(r => {
            const genre = r.food_genre || '기타';
            const distance = r.distance_category || '정보없음';
            const rating = Math.floor(r.rating || 0);
            
            genreCount[genre] = (genreCount[genre] || 0) + 1;
            distanceCount[distance] = (distanceCount[distance] || 0) + 1;
            if (rating >= 1 && rating <= 5) {
                ratingDistribution[rating]++;
            }
        });

        let statsHtml = '<h2>📊 상세 통계</h2>';
        
        statsHtml += '<h3>🍽️ 장르별 분포</h3>';
        Object.entries(genreCount)
            .sort((a, b) => b[1] - a[1])
            .forEach(([genre, count]) => {
                const percentage = ((count / allRestaurants.length) * 100).toFixed(1);
                statsHtml += `<p>${genre}: ${count}개 (${percentage}%)</p>`;
            });
        
        statsHtml += '<h3>🚶‍♂️ 거리별 분포</h3>';
        Object.entries(distanceCount)
            .forEach(([distance, count]) => {
                const percentage = ((count / allRestaurants.length) * 100).toFixed(1);
                statsHtml += `<p>${distance}: ${count}개 (${percentage}%)</p>`;
            });

        statsHtml += '<h3>⭐ 평점별 분포</h3>';
        Object.entries(ratingDistribution)
            .reverse()
            .forEach(([rating, count]) => {
                if (count > 0) {
                    const percentage = ((count / allRestaurants.length) * 100).toFixed(1);
                    statsHtml += `<p>${rating}점대: ${count}개 (${percentage}%)</p>`;
                }
            });

        resultCard.innerHTML = statsHtml;
    };

    // AI 기능 초기화
    function initializeAI() {
        const aiButton = document.getElementById('ai-button');

        // API 키 초기화
        const apiKey = API_CONFIG.GEMINI_API_KEY;
        geminiAI = new GeminiRecommendation(apiKey);

        // AI 추천 받기 버튼 클릭
        aiButton.addEventListener('click', async () => {
            await getAIRecommendation();
        });
    }

    // AI 추천 실행
    async function getAIRecommendation() {
        const loadingDiv = document.getElementById('ai-loading');
        const userPromptElement = document.getElementById('user-prompt');

        try {
            // 사용자 프롬프트 가져오기
            const userPrompt = userPromptElement.value.trim();

            if (!userPrompt) {
                alert('추천 요청 내용을 입력해주세요.');
                userPromptElement.focus();
                return;
            }

            // 로딩 표시
            loadingDiv.style.display = 'block';
            resultCard.innerHTML = '<p class="loading">🤖 AI가 맞춤 추천을 생성 중입니다...</p>';

            // 현재 필터링된 레스토랑 사용
            const candidateRestaurants = filteredRestaurants.length > 0 ? filteredRestaurants : allRestaurants;

            if (candidateRestaurants.length === 0) {
                throw new Error('추천할 수 있는 맛집이 없습니다. 필터를 확인해주세요.');
            }

            // AI 추천 요청
            const recommendation = await geminiAI.getRecommendation(userPrompt, candidateRestaurants);

            // 로딩 숨기기
            loadingDiv.style.display = 'none';

            // AI 추천 결과 표시
            renderAIResult(recommendation);

        } catch (error) {
            console.error('AI 추천 오류:', error);
            alert(`AI 추천 중 오류가 발생했습니다: ${error.message}`);
            
            // 로딩 숨기기
            loadingDiv.style.display = 'none';
        }
    }

    // AI 추천 결과 렌더링
    function renderAIResult(recommendation) {
        const { restaurant, reason, tips, isAiRecommendation } = recommendation;
        
        // 카드에 AI 추천 스타일 적용
        resultCard.classList.add('active', 'ai-recommendation');
        
        const walkingTimeText = restaurant.walking_time_min ? 
            `${restaurant.walking_time_min}분` : '정보없음';
        
        const distanceText = restaurant.distance_from_office_m ? 
            `${restaurant.distance_from_office_m}m` : '정보없음';

        const rating = restaurant.rating || 0;
        const reviewCount = restaurant.review_count || 0;
        const stars = generateStars(rating);
        const signatureMenu = restaurant.signature_menu || '추천메뉴';

        resultCard.innerHTML = `
            <div class="ai-badge">🤖 AI 맞춤 추천</div>
            
            ${restaurant.image_url ? `
                <img src="${restaurant.image_url}" alt="${restaurant.name}" class="restaurant-image" 
                     onerror="this.style.display='none'">
            ` : ''}
            
            <h2>🍽️ ${restaurant.name}</h2>
            <div class="genre">${restaurant.food_genre || '기타'}</div>
            <div class="signature-menu">🏆 ${signatureMenu}</div>
            
            <div class="rating-section">
                <span class="rating-stars">${stars}</span>
                <span class="rating-text">${rating}/5.0 (${reviewCount}개 리뷰)</span>
            </div>
            
            <div class="ai-reason">
                <strong>🤖 AI 추천 이유:</strong><br>
                ${reason}
            </div>
            
            <div class="ai-tips">
                <strong>💡 AI 팁:</strong><br>
                ${tips}
            </div>
            
            <p><strong>🏢 그레이츠숙례에서:</strong></p>
            <p class="distance"><strong>🚶‍♂️ ${distanceText} (도보 ${walkingTimeText})</strong></p>
            <p><strong>🎯 거리감:</strong> ${restaurant.distance_category || '보통'}</p>
            <p><strong>📍 위치:</strong> ${restaurant.location_description || '남대문/중구 일대'}</p>
            
            ${restaurant.naver_map_link ? `
                <div class="naver-link">
                    <a href="${restaurant.naver_map_link}" target="_blank" rel="noopener">
                        🗺️ 네이버 지도에서 보기
                    </a>
                </div>
            ` : ''}
        `;

        console.log('AI 추천 완료:', recommendation);
    }

    // 페이지 로드 시 데이터 불러오기
    loadData();
});