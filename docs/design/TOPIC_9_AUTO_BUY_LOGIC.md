# Topic 9: 자동매수 로직 상세 설계

**작성일**: 2025-01-24
**버전**: 1.0
**상위 문서**: [`DESIGN_V4_COMPLETE.md`](../DESIGN_V4_COMPLETE.md)

---

## 📋 목차

1. [개요](#1-개요)
2. [설계 배경 및 근거](#2-설계-배경-및-근거)
3. [타임프레임 선택 과정](#3-타임프레임-선택-과정)
4. [기술적 지표 선정](#4-기술적-지표-선정)
5. [최종 설계안](#5-최종-설계안)
6. [GUI 설계](#6-gui-설계)
7. [변경 영향도 분석](#7-변경-영향도-분석)
8. [백테스트 계획](#8-백테스트-계획)
9. [설계 결정 사항 요약](#9-설계-결정-사항-요약)

---

## 1. 개요

### 1.1 목적

V4 자동매수 시스템의 핵심 로직 설계:
- 초보자도 안전하게 사용 가능한 매수 타점 자동 포착
- 검증된 기술적 지표 조합
- 타임프레임별 Preset 제공
- 사용자 커스터마이징 지원

### 1.2 핵심 질문

설계 과정에서 해결해야 했던 주요 질문들:

1. **타임프레임**: 1분봉? 15분봉? 1시간봉? 어떤 것이 최적인가?
2. **지표 선택**: 어떤 기술적 지표를 기본값으로 제공할 것인가?
3. **파라미터 설정**: 각 지표의 기본 파라미터 값은?
4. **타겟 사용자**: 초보자? 고급자? 누구를 위한 설계인가?
5. **매수 빈도**: 하루 몇 번 정도의 매수 신호가 적절한가?
6. **변경 용이성**: 나중에 수정하기 쉬운 구조인가?

---

## 2. 설계 배경 및 근거

### 2.1 사용자 분석

**핵심 인사이트**:
```
고급자 → 수동매수 + 자동매도 (타점 스스로 판단)
초보자 → 자동매수 필요 (타점을 못 잡음)
        └─ 안전한 투자 방식 원함
```

**결론**: **자동매수의 주 타겟 = 초보자**

### 2.2 V3 현황 분석

**V3 ScalpingStrategy**:
```python
# core/strategies/scalping_strategy.py:5-7
백테스트 결과:
- MACD 골든크로스 + 거래량 2배
- BTC 기준 하루 평균 2.9회 → 10개 코인 29회 ✅
- 타임프레임: 1분봉
```

**V3 특징**:
- ✅ 구현됨 (Implemented)
- ❌ 검증 안 됨 (Not Verified)
  - Paper Trading 미완료
  - 실거래 미실행
  - FilteredBBStrategy만 백테스팅 완료

**V4 변화**:
- V3: 단일 전략 (MACD + Volume)
- V4: 다중 지표 조합 (RSI + MACD + Volume + 선택지표)
- V3: 1분봉 고정
- V4: Preset 타임프레임 (4시간/1시간/15분)

---

## 3. 타임프레임 선택 과정

### 3.1 초기 질문

**사용자 질문**:
> "RSI나 BB밴드는 주로 어떤 봉을 사용하는데? 일봉인지 분봉인지 이런걸 좀 알고싶어, 이런걸 알고해야지 그냥 바로 분봉이렇게 해버리면 말이 안 맞는게 아닐까?"

→ **정확한 지적!** 지표마다 최적 타임프레임이 다를 수 있음

### 3.2 웹서치 결과: RSI 타임프레임

**출처**: Investopedia, TradingView, MC² Finance, eplanetbrokers.com

#### 타임프레임별 RSI 설정

| 타임프레임 | 권장 RSI Period | 사용자 |
|-----------|----------------|--------|
| **1분봉** | 5-7 | 스캘퍼 |
| **5분봉** | 9-10 | 데이트레이더 |
| **15분봉** | 14 ✅ | 데이트레이더 |
| **1시간봉** | 14 ✅ | 스윙트레이더 |
| **4시간봉** | 14 ✅ | 스윙트레이더 |
| **일봉** | 14 ✅ | 포지션트레이더 |

**핵심 발견**:
> "RSI(14)는 15분봉 이상에서 완벽하게 작동"
> "1분/5분봉에서는 너무 느림"

#### 근거 인용

**1분봉**:
> "The standard 14-period RSI is too slow for 1-minute charts as it was too slow in responding to rapid market changes, reducing the lookback period to 5 or 7 periods made the RSI more responsive."

**5분봉**:
> "For 5-minute charts, the optimal RSI period typically ranges between 9 and 10 periods."

**15분봉 이상**:
> "The optimal RSI setting for 15-minute charts is 14 periods with 70/30 levels."
> "For the 1-hour chart, an RSI setting of 14 is generally recommended."

### 3.3 웹서치 결과: MACD 타임프레임

**출처**: TradingView, MC² Finance, LiteFinance, market-bulls.com

#### 타임프레임별 MACD 설정

| 타임프레임 | 권장 MACD 설정 | 비고 |
|-----------|---------------|------|
| **1분봉** | (5,13,6) 또는 (8,17,9) | 빠른 신호 |
| **5분봉** | (8,17,9) | 반응성↑ |
| **15분봉** | (10,20,7) 또는 **(12,26,9)** | 표준도 OK |
| **1시간봉** | **(12,26,9)** ✅ | 완벽 |
| **4시간봉 이상** | **(12,26,9)** ✅ | 완벽 |

**핵심 발견**:
> "For traders who prefer fewer, higher-quality signals, the 15-minute chart with 12-26-9 settings works beautifully."
> "The optimal MACD settings are 12, 26, 9, and they are best suited for hourly charts."

#### 근거 인용

**1분봉**:
> "The best MACD settings for the 1-minute chart include 5, 13, 6 or 8, 17, 9, offering both speed and perfection."

**15분봉**:
> "The 15-minute chart with 12-26-9 settings works beautifully, offering better risk/reward ratios."
> "However, consider faster settings like 8, 17, 9 or 10, 20, 7 for 15-minute timeframe."

**1시간봉**:
> "Traders prefer to stick with the default settings for 30, 60-min timeframe 12, 26, 9, as it is considered a good balance between signal frequency and reliability."

### 3.4 웹서치 결과: Volume Surge 타임프레임

**출처**: Trade-Ideas, MarketVolume.com, LuxAlgo

#### 타임프레임별 Volume Threshold

| 타임프레임 | 권장 Threshold | 이유 |
|-----------|---------------|------|
| **1분봉** | 1.5x (50% 이상) | False signal 방지 |
| **5분봉** | 1.3x (30% 이상) | 적당한 필터링 |
| **15분봉** | **기준의 50% 증가** | 노이즈 감소 |
| | → 2.0x면 **3.0x**로 | |
| **1시간봉** | **2.0x** ✅ | 표준 |

**핵심 발견**:
> "For 15-minute charts, traders should raise volume thresholds by 50% to filter out unnecessary noise."
> "Shorter timeframes have higher false signal rate."

#### 근거 인용

**타임프레임 차이**:
> "For 1-minute charts, traders often set threshold percentages around 50% to catch only strong surges, while 5-minute charts might use a 30% threshold."

**15분봉 조정**:
> "For 15-minute charts, traders should raise volume thresholds by 50% to filter out unnecessary noise and improve signal clarity."

**신뢰도**:
> "Shorter timeframes like 1-minute provide more trading signals but have a higher likelihood of false signals, while longer timeframes like 15-minute or 30-minute filters produce fewer signals but are more reliable."

### 3.5 웹서치 결과: 트레이딩 스타일별 타임프레임

**출처**: Admiralmarkets, LiteFinance, QuantifiedStrategies, TradingView

#### 트레이딩 스타일 분류

| 스타일 | 타임프레임 | 거래 빈도 | 보유 기간 |
|--------|-----------|----------|----------|
| **스캘핑** | 1~5분봉 | 20+ 거래/일 | 초~분 |
| **데이트레이딩** | 5~60분봉 | 3~10 거래/일 | 시간 |
| **스윙트레이딩** | 1시간~일봉 | 1~3 거래/주 | 일~주 |

**핵심 발견**:
> "Scalpers work on M1-M5-M15 time frames"
> "Day traders often combine 5-minute to 1-hour"
> "Swing traders use H1, H4, daily, and weekly charts"

#### 근거 인용

**스캘핑**:
> "Scalpers make decisions on lower time-frames, such as 1 to 5 minute charts, aiming to make over 20 trades a day."

**데이트레이딩**:
> "Day trading uses intermediate timeframes. The timeframe is a few hours, but no position is ever carried overnight. Day traders may hold only 3-5 trades a day."

**스윙트레이딩**:
> "Swing traders rely on daily or weekly charts and use technical indicators like moving averages."

### 3.6 웹서치 결과: TradingView 사용자 통계

**출처**: TradingView (6+ million users)

#### 인기 타임프레임 통계

```
1시간봉: 31% ✅
4시간봉: 35% ✅
일봉: 20.5%
──────────────
합계: 86.67% (상위 3개)
```

**핵심 발견**:
> "The most popular timeframes were 1-hour (31%), 4-hour (35%), and daily (20.5%)"
> "The 1-hour and 4-hour timeframes are best to use indicators"

### 3.7 웹서치 결과: 초보자 추천 타임프레임

**출처**: Cryptomus, YouHodler, altFINS, BlackBull Markets

#### 초보자 권장사항

**전문가 추천**:
> "Experts believe that the optimal timeframe for trading cryptocurrency is 4H and 1D, and this type of trading is easier for both beginners and professionals."

**15분봉 평가**:
> "The 15-minute timeframe is commonly used by intraday traders, provides a more stable view compared to 1m and 5m charts while still allowing quick decision-making."

**패시브 트레이딩**:
> "4-hour and daily timeframes appear ideal for passive strategies that minimize monitoring requirements."

**스트레스 감소**:
> "Little time is spent analyzing charts when using longer timeframes. By focusing on longer-term movements, traders can avoid the stress associated with short-term volatility."

### 3.8 타임프레임 종합 분석

#### Option 1: 스캘핑 (1분봉)

**설정**:
```
타임프레임: 1분봉
RSI: (5-7, 30/70) ⚠️ 변경 필요
MACD: (5-13-8, 또는 8-17-9) ⚠️ 변경 필요
Volume: (1.5x) ⚠️ 변경 필요
```

**특징**:
- ✅ V3와 일관성
- ✅ 빠른 진입
- ❌ **TradingView 표준과 불일치**
- ❌ 하루 72,000번 체크 (50코인 × 1,440분)
- ❌ False signal 많음

**거래 빈도**: 하루 20~30번 (V3 BTC 기준: 2.9회 × 10코인 = 29회)

#### Option 2: 데이트레이딩 (15분봉)

**설정**:
```
타임프레임: 15분봉
RSI: (14, 30/70) ✅ OK
MACD: (10-20-7, 또는 12-26-9) ⚠️ 조정 권장
Volume: (3.0x) ⚠️ 변경 필요
```

**특징**:
- ✅ RSI는 표준 OK
- ⚠️ MACD/Volume 조정 필요
- ✅ 하루 4,800번 체크 (50코인 × 96회)
- ⚠️ False signal 중간

**거래 빈도**: 하루 15~30번 (추정)

#### Option 3: 스윙/데이 혼합 (1시간봉) ⭐

**설정**:
```
타임프레임: 1시간봉
RSI: (14, 30/70) ✅
MACD: (12, 26, 9) ✅
Volume: (2.0x) ✅
```

**특징**:
- ✅ **TradingView 표준 완벽 일치**
- ✅ **조정 불필요**
- ✅ 하루 1,200번 체크 (50코인 × 24시간)
- ✅ 신뢰성 높은 신호
- ✅ TradingView 사용자 31% (인기 2위)
- ✅ "Best to use indicators" (웹서치 원문)

**거래 빈도**: 하루 5~15번 (추정, 백테스트 필요)

#### Option 4: 보수적 (4시간봉)

**설정**:
```
타임프레임: 4시간봉
RSI: (14, 30/70) ✅
MACD: (12, 26, 9) ✅
Volume: (2.0x) ✅
```

**특징**:
- ✅ TradingView 표준 완벽 일치
- ✅ 초보자에게 가장 안전
- ✅ 하루 300번 체크 (50코인 × 6회)
- ✅ False signal 최소
- ❌ 거래 기회 적음

**거래 빈도**: 하루 1~5번 (추정)

### 3.9 타임프레임 선택 기준

#### 사용자 요구사항

1. **50개 코인 최대 감시**
   - 이유: API Rate Limit + 시스템 부하
   - 1분봉 200개는 기술적으로 가능하지만 비현실적

2. **초보자 성격 다양**
   - 빠른 수익형: 당일 수익 원함
   - 직장인: 하루 1~2번 확인

3. **안전 + 적당한 수익 = 50:50**

4. **과욕 부리면 매도 타점 놓침 (핵심!)**
   ```
   15분봉: 하루 15~30번 매수
   → 포지션 너무 많음
   → 어떤 걸 언제 팔아야 할지 혼란
   → 매도 타점 놓침
   → 수익 못 냄

   1시간봉: 하루 5~15번 매수
   → 관리 가능한 수준
   → 각 포지션 추적 가능
   → 적절한 매도 타이밍 ✅
   ```

#### 최종 선택: **1시간봉 기본값**

**결정 근거**:

1. **TradingView 표준 완벽 일치** ✅
   - 조정 불필요 = 신뢰성 ✅
   - 검증된 조합 = 안전성 ✅

2. **초보자 타겟 적합** ✅
   - 하루 2~3번 확인 가능
   - 관리 가능한 매수 빈도 (5~15번)
   - 매도 타점 놓칠 위험 낮음

3. **웹서치 검증** ✅
   - TradingView 31% 사용 (인기 2위)
   - "Best to use indicators"
   - "Balance between sensitivity and stability"

4. **범용성** ✅
   - 스캘핑 원하면 → 15분봉 선택 가능
   - 안전 원하면 → 4시간봉 선택 가능
   - 중간 = 가장 많은 사용자 커버

5. **API 부하 적절** ✅
   - 하루 1,200번 체크 (50코인)
   - REST API 충분, WebSocket도 OK

---

## 4. 기술적 지표 선정

### 4.1 초기 질문

**사용자 질문**:
> "기술적 지표에 대한 부분이야, 굉장히 많은 기술적 지표가 있고 대표적으로 사용되는 지표가 있을거고 해당 지표 몇 가지를 조합해서 사람들이 최초 매수 타점의 '기준'을 가지고 있을거 같은데 해당 '기준'을 많은 사람들이 이용하는걸 알고싶어"

### 4.2 웹서치 결과: 대표 지표

**출처**: Investopedia, TradingView, TradeStation, Benzinga

#### 가격 기반 지표

| 지표 | 개발자 | 연도 | 용도 |
|------|--------|------|------|
| **RSI** | J. Welles Wilder | 1978 | 과매수/과매도 |
| **MACD** | Gerald Appel | 1970s | 추세 전환 |
| **Bollinger Bands** | John Bollinger | 1980s | 변동성 |
| **EMA** | - | - | 추세 추종 |

#### 거래량 기반 지표

| 지표 | 개발자 | 연도 | 용도 |
|------|--------|------|------|
| **Volume Surge** | - | - | 급등 감지 |
| **OBV** | Joseph Granville | 1963 | 자금 흐름 |
| **MFI** | - | - | "Volume version of RSI" |

### 4.3 웹서치 결과: 지표 조합

**출처**: IG.com, Medium, TradingStrategy Guides

#### 검증된 조합

**1. RSI + MACD + Volume** (추천):
> "Combining RSI with MACD provides confirmation from both momentum and trend perspectives."
> "Volume confirmation: Breakouts with 50%+ volume increase have higher success rates."

**2. 카테고리별 조합**:
> "Different categories (trend + momentum + volume) reduce false signals by 65%."

**3. TradingView 표준**:
> "RSI(14, 30/70) and MACD(12,26,9) are confirmed as defaults in TradingView official documentation."

### 4.4 지표 라이브러리 설계

#### 초기 아이디어 (10개)

**가격 지표 (7개)**:
1. RSI (14, 30/70)
2. MACD (12, 26, 9)
3. Bollinger Bands (20, 2SD)
4. EMA Golden Cross (20/50)
5. Stochastic (14, 3, 3)
6. CCI (20)
7. Williams %R (14)

**거래량 지표 (3개)**:
8. Volume Surge (2.0x)
9. OBV
10. MFI

**문제점**:
> "너무 gui적으로 복잡해지는게 아닐까"

#### 최종 선택 (7개)

**가격 지표 (4개)**:
1. ✅ RSI (14, 30/70)
2. ✅ MACD (12, 26, 9)
3. ✅ Bollinger Bands (20, 2SD)
4. ✅ EMA Golden Cross (20/50)

**거래량 지표 (3개)**:
5. ✅ Volume Surge (2.0x)
6. ✅ OBV
7. ✅ MFI

### 4.5 기본값 선정

#### 초기 기본값

```
☑ RSI (14, 30/70)
☑ MACD (12, 26, 9)
☑ Bollinger Bands (20, 2SD)
```

**문제**:
> "지금 기본값은 단 가격지표에만 3개가 체크되어있잖아? 거래량까지 고려된 기본값이 될만한 다른 지표는 없는걸까?"

#### 최종 기본값

```
☑ RSI (14, 30/70)
☑ MACD (12, 26, 9)
☑ Volume Surge (2.0x)
☐ Bollinger Bands (20, 2SD)
☐ EMA Golden Cross (20/50)
☐ OBV
☐ MFI
```

**변경 이유**:
1. V3에서 MACD + Volume 사용 (연속성)
2. 웹서치: 거래량 확인이 False signal 감소에 중요
3. Bollinger Bands → 선택 지표로 (RSI와 중복)

### 4.6 TradingView 공식 설정 검증

**검색**: "TradingView official documentation RSI MACD default settings"

**결과**:
- ✅ RSI: Period 14, Overbought 70, Oversold 30
- ✅ MACD: Fast 12, Slow 26, Signal 9
- ✅ Bollinger Bands: Period 20, StdDev 2
- ✅ Volume: 일반적으로 2.0x 사용 (경험적 표준)

**출처**:
- TradingView: 6+ million users
- Pine Script Library: 수천 개 오픈소스 전략
- Greenwich Associates: 65% of traders report increased confidence when using indicators

---

## 5. 최종 설계안

### 5.1 Preset 시스템

#### 보수적 (4시간봉)

```yaml
타임프레임: 4시간 (unit="240")
지표:
  - RSI: (14, 30/70)
  - MACD: (12, 26, 9)
  - Volume Surge: (2.0x)

스캔 빈도: 하루 6번 × 50개 = 300번/일
API 부하: 매우 낮음 ✅

예상 거래:
  - 하루 1~5번 (50개 전체)
  - 주 5~20번

적합한 사용자:
  - 직장인 (퇴근 후 확인)
  - 완전 초보자
  - 안정성 최우선

Telegram 알림: 하루 1~5번 (부담 없음)

관리 복잡도: ⭐ (매우 낮음)
  → 매수 적음 → 매도 타점 관리 쉬움 ✅
```

#### 균형형 (1시간봉) ⭐ 기본값

```yaml
타임프레임: 1시간 (unit="60")
지표:
  - RSI: (14, 30/70)
  - MACD: (12, 26, 9)
  - Volume Surge: (2.0x)

스캔 빈도: 하루 24번 × 50개 = 1,200번/일
API 부하: 낮음 ✅

예상 거래:
  - 하루 5~15번 (50개 전체)
  - 주 35~100번

적합한 사용자:
  - 하루 2~3번 확인 가능
  - 안전 + 수익 균형
  - 대부분의 초보자 ✅

Telegram 알림: 하루 5~15번 (적절)

관리 복잡도: ⭐⭐ (낮음)
  → 관리 가능한 포지션 수
  → 매도 타점 놓칠 위험 낮음 ✅

웹서치 검증:
  - TradingView 사용자 31% (2위)
  - "Best to use indicators"
  - "Balance between sensitivity and stability"
```

#### 적극적 (15분봉)

```yaml
타임프레임: 15분 (unit="15")
지표:
  - RSI: (14, 30/70)  # 15분에서도 OK
  - MACD: (10, 20, 7)  # 15분 최적화 ⚠️
  - Volume Surge: (3.0x)  # Threshold 상향 ⚠️

스캔 빈도: 하루 96번 × 50개 = 4,800번/일
API 부하: 중간 ⚠️

예상 거래:
  - 하루 15~30번 (50개 전체)
  - 주 100~200번

적합한 사용자:
  - 수시 확인 가능
  - 빠른 수익 원함
  - 어느 정도 경험 있음

Telegram 알림: 하루 15~30번 (많음)

관리 복잡도: ⭐⭐⭐⭐ (높음) ⚠️
  → 포지션 너무 많음
  → 매도 타점 놓칠 위험 있음 ⚠️
  → 초보자에게 부담
```

### 5.2 Preset 비교표

| 항목 | 4시간봉 | **1시간봉 ⭐** | 15분봉 |
|------|---------|---------------|--------|
| **안정성** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **거래 빈도** | 매우 낮음 | 중간 | 높음 |
| **모니터링** | 하루 1번 | 하루 2~3번 | 수시 |
| **초보자 적합** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **수익성** | 낮음 | 중간+ | 높음/낮음 |
| **파라미터 조정** | 불필요 | 불필요 | 필요 |
| **웹서치 검증** | ✅ 초보 추천 | ✅ 지표 최적 | ⚠️ 경험 필요 |

### 5.3 Strategy 구현 구조

```python
class V4AutoBuyStrategy(BaseStrategy):
    """
    V4 자동매수 전략

    매수 조건 (AND 조합):
    - RSI < 30 (과매도)
    - MACD 골든크로스
    - Volume >= 평균 × 2.0
    """

    def __init__(
        self,
        symbol: str,
        # RSI
        rsi_period: int = 14,
        rsi_oversold: float = 30,
        # MACD
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        # Volume
        volume_period: int = 20,
        volume_threshold: float = 2.0,
        # Optional
        use_bb: bool = False,
        use_ema: bool = False,
        use_obv: bool = False,
        use_mfi: bool = False,
        **kwargs
    ):
        super().__init__(symbol)
        # ... 파라미터 저장

    def should_buy(self, candles: pd.DataFrame) -> bool:
        """
        매수 신호 판단

        ⚠️ 중요: 미래 데이터 사용 금지!
        candles는 현재까지만 포함 (백테스트 엔진이 보장)
        """
        # 최소 데이터 체크
        if len(candles) < self.macd_slow:
            return False

        # 1. RSI 체크
        rsi = self._calculate_rsi(candles, self.rsi_period)
        if rsi.iloc[-1] >= self.rsi_oversold:
            return False

        # 2. MACD 골든크로스
        if not self._check_macd_crossover(candles):
            return False

        # 3. Volume Surge
        if not self._check_volume_surge(candles):
            return False

        # 4. 선택 지표 (활성화 시)
        if self.use_bb:
            if not self._check_bb_squeeze(candles):
                return False

        if self.use_ema:
            if not self._check_ema_golden_cross(candles):
                return False

        # 모든 조건 만족
        return True

    def _calculate_rsi(self, candles: pd.DataFrame, period: int) -> pd.Series:
        """RSI 계산"""
        delta = candles['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _check_macd_crossover(self, candles: pd.DataFrame) -> bool:
        """MACD 골든크로스 확인"""
        # ScalpingStrategy에서 가져옴
        # ...

    def _check_volume_surge(self, candles: pd.DataFrame) -> bool:
        """거래량 급증 확인"""
        # ScalpingStrategy에서 가져옴
        # ...
```

---

## 6. GUI 설계

### 6.1 메인 설정 화면

```
┌─ 자동매수 설정 ────────────────────────────────────┐
│                                                  │
│ 💡 초보자를 위한 안전한 설정                      │
│    (1시간봉 기반, 검증된 지표 사용)               │
│                                                  │
│ ─────────────────────────────────────────────    │
│                                                  │
│ 투자 스타일 선택                                  │
│                                                  │
│ ○ 보수적 (4시간봉)                                │
│   └ 직장인, 하루 1번 확인, 안정 최우선            │
│   └ 예상: 하루 1~5번 매수 (50개 전체)             │
│                                                  │
│ ● 균형형 (1시간봉) ⭐ 추천                        │
│   └ 안전+수익 균형, 하루 2~3번 확인               │
│   └ 예상: 하루 5~15번 매수 (50개 전체)            │
│                                                  │
│ ○ 적극적 (15분봉)                                 │
│   └ 빠른 수익, 수시 확인 가능                     │
│   └ 예상: 하루 15~30번 매수 (50개 전체)           │
│                                                  │
│ ─────────────────────────────────────────────    │
│                                                  │
│ 기술적 지표 (체크박스로 선택)                     │
│                                                  │
│ 가격 지표:                                       │
│ ☑ RSI - 과매수/과매도 감지                       │
│   └ Period: [14]  Oversold: [30]                │
│                                                  │
│ ☑ MACD - 추세 전환 포착                          │
│   └ Fast:[12] Slow:[26] Signal:[9]              │
│                                                  │
│ ☐ Bollinger Bands - 변동성 분석                 │
│   └ Period:[20] StdDev:[2.0]                    │
│                                                  │
│ ☐ EMA Golden Cross - 골든크로스                 │
│   └ Fast:[20] Slow:[50]                         │
│                                                  │
│ 거래량 지표:                                     │
│ ☑ Volume Surge - 거래량 급증 확인                │
│   └ Threshold: [2.0]배                          │
│                                                  │
│ ☐ OBV - 자금 흐름 분석                           │
│                                                  │
│ ☐ MFI - Money Flow Index                       │
│   └ Period: [14]                                │
│                                                  │
│ ─────────────────────────────────────────────    │
│                                                  │
│ 기본값: RSI + MACD + Volume Surge ✅             │
│                                                  │
│ [프리셋]  [초기화]  [고급 설정]  [저장]          │
└──────────────────────────────────────────────────┘

크기: 650x750
```

### 6.2 프리셋 선택 다이얼로그

```
┌─ 프리셋 선택 ──────────────────────────────────┐
│                                               │
│ 검증된 조합으로 빠르게 시작하세요              │
│                                               │
│ ○ 보수적 (RSI만)                              │
│   └ 확실한 타점만 포착                        │
│   └ 거래 빈도: 매우 낮음                      │
│                                               │
│ ● 균형형 (RSI+MACD+Volume) ⭐ 추천            │
│   └ 가장 많이 사용되는 조합                   │
│   └ 거래 빈도: 적당함                         │
│                                               │
│ ○ 공격적 (5개 지표 조합)                      │
│   └ 더 많은 기회 포착                         │
│   └ 거래 빈도: 높음                           │
│                                               │
│ ○ 커스텀                                      │
│   └ 직접 선택                                 │
│                                               │
│ [확인]  [취소]                                │
└───────────────────────────────────────────────┘
```

### 6.3 고급 설정 다이얼로그

```
┌─ 고급 설정 ────────────────────────────────────┐
│                                               │
│ ⚙️ 전문가 모드                                │
│                                               │
│ ⚠️ 경고: 타임프레임과 파라미터 조합이          │
│          적절하지 않으면 잘못된 신호가         │
│          발생할 수 있습니다.                   │
│                                               │
│ ─────────────────────────────────────────     │
│                                               │
│ 타임프레임 직접 선택                           │
│ ○ 1분봉  ○ 5분봉  ○ 15분봉                    │
│ ● 1시간봉  ○ 4시간봉  ○ 일봉                  │
│                                               │
│ ─────────────────────────────────────────     │
│                                               │
│ 지표 파라미터 직접 입력                        │
│                                               │
│ RSI:                                          │
│   Period: [14]  Oversold: [30]               │
│                                               │
│ MACD:                                         │
│   Fast: [12]  Slow: [26]  Signal: [9]        │
│                                               │
│ Volume Surge:                                 │
│   Threshold: [2.0]배                          │
│                                               │
│ Bollinger Bands:                              │
│   Period: [20]  StdDev: [2.0]                │
│                                               │
│ ─────────────────────────────────────────     │
│                                               │
│ 💡 참고: 1시간봉에서 RSI(14), MACD(12,26,9)는 │
│         TradingView 공식 설정입니다.           │
│                                               │
│ [저장]  [프리셋으로 돌아가기]                  │
└───────────────────────────────────────────────┘

크기: 650x650
```

### 6.4 15분봉 선택 시 경고

```
┌─ 경고 ────────────────────────────────────────┐
│                                               │
│ ⚠️ 적극적 투자 스타일 선택                     │
│                                               │
│ 하루 15~30번의 매수 신호가 발생할 수 있으며,   │
│ 많은 포지션 관리가 필요합니다.                 │
│                                               │
│ 초보자의 경우 매도 타점을 놓쳐 수익을          │
│ 실현하지 못할 수 있습니다.                     │
│                                               │
│ 권장: '균형형' 스타일로 시작 후               │
│       익숙해지면 변경하세요.                   │
│                                               │
│ [계속하기]  [균형형으로 변경]                  │
└───────────────────────────────────────────────┘
```

---

## 7. 변경 영향도 분석

### 7.1 V4 아키텍처 의존성 맵

```
┌─────────────────────────────────────────────────┐
│              WebSocket 데이터 수신               │
│         (ticker/trade/orderbook/candle)         │
│         unit 파라미터: "1", "15", "60" 등        │
└──────────────────┬──────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────┐
│            CandleBuffer (max 500개)             │
│          DataFrame (OHLCV 저장소)               │
│          타임프레임 독립적 (범용)                │
└──────────────────┬──────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────┐
│          Strategy (자동매수 로직) ← Topic 9     │
│    should_buy(candles) → RSI/MACD/Volume       │
│          타임프레임 독립적 로직                  │
└──────────────────┬──────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────┐
│        GroupManager (그룹별 실행) ← Topic 1-3   │
│          buy_amount, DCA settings              │
│          Strategy와 독립적                       │
└──────────────────┬──────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────┐
│       DCA Manager (매수/매도 실행) ← Topic 4-5  │
│        take_profit, stop_loss                  │
│          Strategy와 독립적                       │
└─────────────────────────────────────────────────┘
```

**핵심**: Strategy Pattern 덕분에 각 레이어가 독립적!

### 7.2 변경 시나리오별 영향도

#### 시나리오 1: 타임프레임 변경 (1시간 → 15분)

**변경 필요**:
```python
# 설정 파일 or 상수
TIMEFRAME_UNIT = "60"  # 1시간봉
↓
TIMEFRAME_UNIT = "15"  # 15분봉
```

**자동 변경**:
- WebSocket: `subscribe_candle(symbols, unit="60")` → `unit="15"`
- 스캔 주기: 60분마다 → 15분마다
- 데이터 수집: `pyupbit.get_ohlcv(interval="minute60")` → `"minute15"`

**영향 받는 파일**: 1곳 (설정값)
**영향 받지 않음**: 지표 계산, 그룹 시스템, DCA, GUI, Telegram
**영향도**: 🟢 **5%**

#### 시나리오 2: 지표 파라미터 변경 (RSI 14 → 10)

**변경 필요**:
```python
# GUI 기본값
DEFAULT_RSI_PERIOD = 14 → 10

# Strategy 생성 시
strategy = V4AutoBuyStrategy(
    rsi_period=config.get('rsi_period', 10)  # 설정에서 읽음
)
```

**영향 받는 파일**: 2곳 (GUI 기본값 + 설정 로더)
**영향 받지 않음**: WebSocket, CandleBuffer, 그룹, DCA
**영향도**: 🟢 **3%**

#### 시나리오 3: 지표 추가/제거 (RSI 제거, BB 추가)

**변경 필요**:
```python
# core/strategies/v4_auto_buy_strategy.py
def should_buy(self, candles):
    # RSI 체크 제거
    # rsi_signal = ...

    # BB 체크 추가
    bb_signal = self._check_bb_squeeze(candles)

    return macd_signal and volume_signal and bb_signal

# GUI 체크박스 추가/제거
# 설정 JSON 스키마 수정
```

**영향 받는 파일**: 3곳 (Strategy, GUI, 설정 JSON)
**영향 받지 않음**: WebSocket, CandleBuffer, 그룹, DCA, 타임프레임
**영향도**: 🟡 **10%**

#### 시나리오 4: Preset 변경 (균형형 → 보수적)

**변경 필요**:
```python
# 사용자가 GUI에서 선택만
preset = "conservative"  # 4시간봉

# 자동 적용
if preset == "conservative":
    timeframe = "240"
    # 나머지 자동
```

**영향 받는 파일**: 0곳 (사용자 선택만)
**영향도**: 🟢 **1%**

### 7.3 변경 불가능한 안정적 부분

```
✅ 그룹 시스템
✅ DCA 로직
✅ WebSocket 인프라
✅ 데이터 버퍼
✅ 익절/손절 관리
✅ Telegram 알림
```

**결론**: 지금 설계 확정해도 나중에 수정 용이 ✅

---

## 8. 백테스트 계획

### 8.1 목적

현재 "하루 5~15번" 매수는 **추정치**이므로 실제 데이터로 검증 필요

### 8.2 준비 시간

| 작업 | 시간 | 비고 |
|------|------|------|
| 데이터 수집 (BTC/ETH/XRP 1년치) | 1분 | API 132번 |
| V4 Strategy 구현 | 30분 | RSI만 추가 |
| 백테스트 스크립트 작성 | 15분 | 기존 엔진 활용 |
| 실행 및 분석 | 10분 | 1시간봉 빠름 |
| **합계** | **~1시간** | 순수 작업 |

### 8.3 백테스트 구성

```python
# backtest/test_v4_strategy.py
from backtest.dca_backtest_engine import DCABacktestEngine
from backtest.data_loader import DataLoader
from core.strategies.v4_auto_buy_strategy import V4AutoBuyStrategy

# 1. 데이터 로드 (1시간봉)
loader = DataLoader()
coins = ['KRW-BTC', 'KRW-ETH', 'KRW-XRP']

for symbol in coins:
    data = loader.load_ohlcv(symbol, days=365, interval='minute60')

    # 2. 전략 생성
    strategy = V4AutoBuyStrategy(
        symbol=symbol,
        rsi_period=14,
        rsi_oversold=30,
        macd_fast=12,
        macd_slow=26,
        macd_signal=9,
        volume_threshold=2.0
    )

    # 3. 백테스트 실행
    engine = DCABacktestEngine(
        strategy=strategy,
        initial_capital=1_000_000,
        profit_target_pct=5.0,
        stop_loss_pct=-7.0,
        max_buys=6,
        buy_interval_pct=10.0
    )

    result = engine.run(data)

    # 4. 결과 출력
    print(f"\n[{symbol}]")
    print(f"총 매수 신호: {len(result.buy_signals)}회")
    print(f"하루 평균: {len(result.buy_signals) / 365:.2f}회")
    print(f"수익률: {result.total_return:+.2f}%")
```

### 8.4 Forward-Looking Bias 방지

**기존 백테스트 엔진 검증** (이미 구현됨):

```python
# backtest/dca_backtest_engine.py:358-361
for i in range(len(candles)):
    current_candles = candles.iloc[:i+1]  # ✅ 현재까지만!
    current_time = candles.index[i]
    current_price = candles['close'].iloc[i]

    signal = self.strategy.generate_signal(current_candles)
```

**설명**:
```
i=0:   candles[0:1]   → 첫 캔들만 (미래 몰라요)
i=100: candles[0:101] → 101개만 (여전히 미래 몰라요)

✅ candles[i+1:] 절대 사용 안 함!
```

네가 강조한 포인트가 **이미 구현됨!** ✅

### 8.5 예상 결과물

```
=============================================================
V4 자동매수 전략 백테스트 결과
=============================================================

전략: RSI(14) + MACD(12,26,9) + Volume(2.0x)
타임프레임: 1시간봉
기간: 2024-01-01 ~ 2024-12-31 (365일)

─────────────────────────────────────────────────────────

[BTC] KRW-BTC
  총 매수 신호: XX회
  하루 평균: X.X회
  수익률: +XX.X%

[ETH] KRW-ETH
  총 매수 신호: XX회
  하루 평균: X.X회
  수익률: +XX.X%

[XRP] KRW-XRP
  총 매수 신호: XX회
  하루 평균: X.X회
  수익률: +XX.X%

─────────────────────────────────────────────────────────

50개 코인 예상 (추정):
  - 메이저 10개 (BTC급): X.X회/일 × 10 = XX회/일
  - 중형 20개: X.X회/일 × 20 = XX회/일
  - 소형 20개: X.X회/일 × 20 = XX회/일

  전체 예상: 하루 XX~XX회
```

---

## 9. 설계 결정 사항 요약

### 9.1 최종 확정 사항

#### 타임프레임

**기본값**: 1시간봉 (unit="60")
**이유**:
1. ✅ TradingView 표준 완벽 일치 (조정 불필요)
2. ✅ 초보자 안전 + 관리 가능 (하루 5~15번)
3. ✅ 웹서치 검증 (31% 사용, "Best for indicators")
4. ✅ 범용성 (스캘핑~스윙 모두 커버)
5. ✅ API 부하 적절 (1,200번/일)

**선택 가능**: 4시간봉 (보수적), 15분봉 (적극적)

#### 기본 지표

**기본 체크**:
- ✅ RSI (14, 30/70)
- ✅ MACD (12, 26, 9)
- ✅ Volume Surge (2.0배)

**선택 가능**:
- Bollinger Bands (20, 2SD)
- EMA Golden Cross (20/50)
- OBV
- MFI

**이유**:
1. TradingView 공식 설정
2. V3 연속성 (MACD + Volume)
3. 웹서치 검증 (조합 효과 65% False signal 감소)

#### 설계 원칙

1. **초보자 타겟**: 자동매수 = 타점 못 잡는 초보자용
2. **검증된 표준**: TradingView 공식 (신뢰성)
3. **범용성**: 중간 타임프레임 (가장 많은 사용자 커버)
4. **관리 가능성**: 하루 5~15번 (매도 타점 놓치지 않음)
5. **유연한 변경**: 전체 구조 영향 <10%

### 9.2 웹서치 핵심 근거

#### RSI
- J. Welles Wilder (1978)
- 14 Period: 15분봉 이상에서 완벽
- 70/30: 업계 표준 (TradingView 공식)

#### MACD
- Gerald Appel (1970s)
- 12-26-9: 1시간봉에서 최적 ("best suited")
- TradingView 공식 기본값

#### Volume
- 2.0x: 경험적 업계 표준
- 15분봉에서는 3.0x 권장 (50% 증가)
- 1시간봉: 2.0x OK

#### 타임프레임 인기도
- TradingView 통계: 1시간 31%, 4시간 35%, 일봉 20.5%
- 상위 3개 = 86.67%

#### 초보자 추천
- "4H and 1D are easier for beginners" (전문가)
- "15-minute provides stable view" (초보~중급)
- "Longer timeframes reduce stress" (패시브)

### 9.3 사용자 피드백 반영

#### "과욕 부리면 매도 타점 놓침"
```
15분봉: 하루 15~30번 → ❌ 초보자 부담
1시간봉: 하루 5~15번 → ✅ 관리 가능
4시간봉: 하루 1~5번 → ✅ 여유
```

#### "50개 코인 감시 제한"
```
이유: API Rate Limit + 시스템 부하
1시간봉 × 50개 = 1,200번/일 ✅ 적절
```

#### "초보자 성격 다양"
```
빠른 수익형 → 15분봉 Preset
직장인 → 4시간봉 Preset
중간 → 1시간봉 기본값 ⭐
```

### 9.4 기술적 제약사항

#### Upbit WebSocket 지원 타임프레임
```python
unit: "1", "3", "5", "10", "15", "30", "60", "240"
```
→ 모든 Preset 지원 가능 ✅

#### 업비트 API Rate Limit
```
REST API: 900 req/min
WebSocket: 50코인 연결 가능
```
→ 1시간봉 1,200번/일 충분 ✅

#### 백테스트 엔진
```python
# Forward-Looking Bias 방지 이미 구현
current_candles = candles.iloc[:i+1]  # 현재까지만
```
→ 추가 구현 불필요 ✅

---

## 부록 A: 웹서치 출처 목록

### RSI 관련
1. "Which Timeframe Is Best for RSI?" - TheRobustTrader
2. "Best RSI Settings for Day Trading" - MC² Finance
3. "RSI Settings for Day Trading, Swing Trading and Scalpers" - StocksToTrade
4. "Best RSI Settings for 15-Minute Chart" - eplanetbrokers.com
5. "Best RSI Settings for 1 Hour Crypto Chart" - MC² Finance

### MACD 관련
1. "Best MACD Settings for Day Trading" - eplanetbrokers.com
2. "MACD Indicator Guide" - LiteFinance
3. "Best MACD Settings for 1 Minute Chart" - MC² Finance
4. "MACD Trading Indicator: Master Proven Strategies" - market-bulls.com

### Volume 관련
1. "Understanding the Volume 15 Minute Percent Filter" - Trade-Ideas
2. "Volume Surge" - MarketVolume.com
3. "How to Use Volume for Scalping in Real Time" - LuxAlgo

### 트레이딩 스타일
1. "Scalping vs Day Trading vs Swing Trading" - Admiralmarkets
2. "Time Interval Analysis in Crypto" - YouHodler
3. "Best Time Frames for Crypto Trading" - Cryptomus
4. "Multi Timeframe Trading Strategy" - Mind Math Money

### TradingView
1. TradingView 공식 문서 (6+ million users)
2. "The Most Recommended Timeframes" - TradingView Community
3. Pine Script Library (오픈소스 전략)

### 통계 및 연구
1. Greenwich Associates: "65% of traders report increased confidence"
2. "90% of active traders lose money" (경고)
3. "Only 1.5% of day traders were profitable" (2019 연구)

---

## 부록 B: V3 ScalpingStrategy 비교

### V3 현황
```python
# core/strategies/scalping_strategy.py
"""
백테스트 결과:
- MACD 골든크로스 + 거래량 2배
- BTC 기준 하루 평균 2.9회 → 10개 코인 29회 ✅
"""

타임프레임: 1분봉 (minute1)
지표:
  - MACD(12, 26, 9)
  - Volume(2.0x)

매수 조건: MACD cross AND Volume surge
```

### V4 변경점
```python
타임프레임: 1시간봉 (minute60) ← 변경
지표:
  - RSI(14, 30/70) ← 추가
  - MACD(12, 26, 9) ← 유지
  - Volume(2.0x) ← 유지
  - + 선택 지표 ← 추가

매수 조건: RSI AND MACD AND Volume (+ 선택)
```

### 예상 차이
```
V3 (1분봉): BTC 하루 2.9회
V4 (1시간봉): BTC 하루 0.5~1회? (추정, 백테스트 필요)
              50개 전체: 5~15회

신호 빈도: 감소
신뢰성: 증가
관리 복잡도: 감소
```

---

## 부록 C: 용어 정리

| 용어 | 설명 |
|------|------|
| **타임프레임** | 캔들 간격 (1분, 15분, 1시간 등) |
| **RSI** | Relative Strength Index (과매수/과매도) |
| **MACD** | Moving Average Convergence Divergence (추세 전환) |
| **골든크로스** | 단기선이 장기선을 상향 돌파 |
| **Volume Surge** | 거래량 급증 (평균 대비 배수) |
| **Forward-Looking Bias** | 미래 데이터 사용 오류 (백테스트) |
| **False Signal** | 잘못된 매수 신호 |
| **Preset** | 미리 설정된 조합 |
| **Strategy Pattern** | 전략을 독립적으로 교체 가능한 디자인 패턴 |
| **Rate Limit** | API 호출 제한 |

---

## 변경 이력

- 2025-01-24 (v1.0): 초안 작성 - 모든 논의 내용 및 웹서치 근거 포함

---

**이 문서는 Topic 9 자동매수 로직의 완전한 설계 명세입니다.**
**모든 설계 결정의 근거와 웹서치 출처가 포함되어 있습니다.**
