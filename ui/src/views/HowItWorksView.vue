<script setup lang="ts">
// Static explainer — no data fetching needed
</script>

<template>
  <div class="hiw">

    <!-- ── Hero ──────────────────────────────────────────────────── -->
    <div class="hero">
      <h2 class="hero-title">How AlphaForge Works</h2>
      <p class="hero-sub">
        Three AI agents run automatically every day to research stocks, trade on your behalf,
        and continuously improve the strategy — all without you lifting a finger.
        The sole objective: <strong>beat the S&amp;P 500.</strong>
      </p>
    </div>

    <!-- ── System overview ───────────────────────────────────────── -->
    <div class="overview-row">
      <div class="ov-agent analyst">
        <div class="ov-icon">🔍</div>
        <div class="ov-name">Market Analyst</div>
        <div class="ov-time">7:30 AM CST</div>
      </div>
      <div class="ov-arrow">→</div>
      <div class="ov-agent trader">
        <div class="ov-icon">📈</div>
        <div class="ov-name">Paper Trader</div>
        <div class="ov-time">3× daily</div>
      </div>
      <div class="ov-arrow">→</div>
      <div class="ov-agent retro">
        <div class="ov-icon">🧠</div>
        <div class="ov-name">Retrospective</div>
        <div class="ov-time">Monthly</div>
      </div>
    </div>
    <p class="overview-caption">
      Each arrow means the next agent depends on the previous one's output.
      The retrospective loops back to improve how the other two agents think.
    </p>

    <!-- ══════════════════════════════════════════════════════════ -->
    <!-- AGENT 1 — MARKET ANALYST                                  -->
    <!-- ══════════════════════════════════════════════════════════ -->
    <section class="agent-section analyst-theme">
      <div class="agent-header">
        <span class="agent-badge analyst-badge">Agent 1</span>
        <h3 class="agent-title">🔍 Market Analyst</h3>
        <span class="schedule-pill">Runs at 7:30 AM CST · Mon–Fri</span>
      </div>
      <p class="agent-desc">
        Think of this as your personal Wall Street research team that wakes up before the market
        opens every morning. It scans the internet for the most talked-about stocks, digs into
        their financials, reads the charts, and scores the news — then hands a shortlist of the
        best opportunities to the Paper Trader.
      </p>

      <div class="flow">
        <div class="flow-step">
          <div class="step-icon">📡</div>
          <div class="step-body">
            <div class="step-title">Step 1 — Trend Spotting</div>
            <div class="step-desc">
              Scans 5 live sources — Yahoo Finance trending, top gainers, StockTwits, NASDAQ
              most-active, and Reddit — to find the 10 stocks getting the most attention right now.
              Stocks that show up in multiple sources get priority.
            </div>
          </div>
        </div>
        <div class="flow-arrow">↓</div>

        <div class="flow-step">
          <div class="step-icon">🏦</div>
          <div class="step-body">
            <div class="step-title">Step 2 — Fundamental Analysis</div>
            <div class="step-desc">
              For each stock, it checks: Is the company growing revenue? Are profits going up?
              How much debt do they carry? Did they beat earnings estimates recently?
              An AI scores every company and flags hidden strengths or red flags the numbers alone don't show.
            </div>
          </div>
        </div>
        <div class="flow-arrow">↓</div>

        <div class="flow-step">
          <div class="step-icon">📊</div>
          <div class="step-body">
            <div class="step-title">Step 3 — Technical Analysis</div>
            <div class="step-desc">
              Looks at the price chart for each stock: Is it trending up? Is it overbought?
              Where are the key support and resistance levels? It uses RSI, MACD, Bollinger Bands,
              and moving averages to find stocks with momentum — not just ones that went up yesterday.
            </div>
          </div>
        </div>
        <div class="flow-arrow">↓</div>

        <div class="flow-step">
          <div class="step-icon">📰</div>
          <div class="step-body">
            <div class="step-title">Step 4 — Sentiment Analysis</div>
            <div class="step-desc">
              Reads recent news headlines for each stock and scores the mood: are analysts upgrading
              it? Did the company just beat earnings? Is there a product launch or buyback?
              Negative signals like lawsuits, downgrades, or insider selling are flagged as risks.
            </div>
          </div>
        </div>
        <div class="flow-arrow">↓</div>

        <div class="flow-step">
          <div class="step-icon">⚡</div>
          <div class="step-body">
            <div class="step-title">Step 5 — Volatility Check</div>
            <div class="step-desc">
              Checks the VIX (the market's "fear gauge") and each stock's beta to understand
              how risky the overall environment is. High VIX means the market is nervous —
              the system becomes more selective.
            </div>
          </div>
        </div>
        <div class="flow-arrow">↓</div>

        <div class="flow-step highlight-step">
          <div class="step-icon">🏆</div>
          <div class="step-body">
            <div class="step-title">Step 6 — Final Picks</div>
            <div class="step-desc">
              An AI synthesises everything — fundamentals, chart setup, sentiment, volatility —
              and selects the <strong>top 5 stocks</strong> most likely to beat the S&amp;P 500
              in the next 30 days. Each pick comes with an entry price, exit target, stop-loss,
              and confidence score. The result is saved as today's Analyst Report.
            </div>
          </div>
        </div>
      </div>

      <div class="output-box analyst-output">
        <span class="output-label">Output</span>
        Today's analyst report with up to 5 stock picks, each with entry price, profit target, stop-loss, and confidence score.
      </div>
    </section>

    <!-- ══════════════════════════════════════════════════════════ -->
    <!-- AGENT 2 — PAPER TRADER                                    -->
    <!-- ══════════════════════════════════════════════════════════ -->
    <section class="agent-section trader-theme">
      <div class="agent-header">
        <span class="agent-badge trader-badge">Agent 2</span>
        <h3 class="agent-title">📈 Paper Trader</h3>
        <span class="schedule-pill">Runs 3× daily · 8:30 AM · 11:00 AM · 1:45 PM CST</span>
      </div>
      <p class="agent-desc">
        This is the agent that actually "places trades" (on paper, not real money — yet).
        It checks your open positions for exit signals, then looks at the analyst's picks
        and decides which ones to buy with available capital. It runs three times a day
        so it can react to intraday price moves.
      </p>

      <div class="flow">
        <div class="flow-step">
          <div class="step-icon">👀</div>
          <div class="step-body">
            <div class="step-title">Step 1 — Monitor Open Positions</div>
            <div class="step-desc">
              Checks every stock currently held. If a stock has fallen to its stop-loss price
              (protecting you from further loss) or risen to its profit target (locking in gains),
              it automatically closes the position. No human needed.
            </div>
          </div>
        </div>
        <div class="flow-arrow">↓</div>

        <div class="flow-step">
          <div class="step-icon">💰</div>
          <div class="step-body">
            <div class="step-title">Step 2 — Book Profits &amp; Losses</div>
            <div class="step-desc">
              When a position is closed, the proceeds are added back to your buying power.
              Profits grow your available capital — meaning future positions can be larger.
              Every trade is logged with the exact P&amp;L.
            </div>
          </div>
        </div>
        <div class="flow-arrow">↓</div>

        <div class="flow-step">
          <div class="step-icon">🤖</div>
          <div class="step-body">
            <div class="step-title">Step 3 — AI Trade Decision</div>
            <div class="step-desc">
              An AI reviews today's analyst picks and decides which ones to buy right now.
              It only buys if: the stock isn't already in the portfolio, the current price
              is within 2% of the analyst's recommended entry price, the confidence score
              meets the threshold, and you have enough buying power. Quality over quantity —
              3 great trades beat 5 mediocre ones.
            </div>
          </div>
        </div>
        <div class="flow-arrow">↓</div>

        <div class="flow-step highlight-step">
          <div class="step-icon">🔒</div>
          <div class="step-body">
            <div class="step-title">Step 4 — Execute &amp; Protect Capital</div>
            <div class="step-desc">
              Buys are executed and the buying power is reduced accordingly.
              A hard cap ensures the total invested in open positions never exceeds
              your available buying power — you can never be over-invested.
              A portfolio snapshot is taken after every run.
            </div>
          </div>
        </div>
      </div>

      <div class="output-box trader-output">
        <span class="output-label">Output</span>
        Updated positions, booked P&amp;L on exits, new buy orders executed, and a portfolio snapshot saved to history.
      </div>
    </section>

    <!-- ══════════════════════════════════════════════════════════ -->
    <!-- AGENT 3 — RETROSPECTIVE                                   -->
    <!-- ══════════════════════════════════════════════════════════ -->
    <section class="agent-section retro-theme">
      <div class="agent-header">
        <span class="agent-badge retro-badge">Agent 3</span>
        <h3 class="agent-title">🧠 Retrospective Analyst</h3>
        <span class="schedule-pill">Runs once a month · Last Sunday · 11 PM CST</span>
      </div>
      <p class="agent-desc">
        Once a month, this agent acts like a fund manager reviewing the team's performance.
        It looks at every trade made during the month, compares the results to what the S&amp;P 500
        returned, finds what went wrong (and right), and rewrites the playbook for next month.
        It is the only thing allowed to change the strategy.
      </p>

      <div class="flow">
        <div class="flow-step">
          <div class="step-icon">📐</div>
          <div class="step-body">
            <div class="step-title">Step 1 — Performance vs S&amp;P 500</div>
            <div class="step-desc">
              Adds up every closed trade's profit and loss for the month and compares it to
              what a simple S&amp;P 500 index investment would have returned on the same capital.
              This is the single most important question: <em>did we beat the market?</em>
            </div>
          </div>
        </div>
        <div class="flow-arrow">↓</div>

        <div class="flow-step">
          <div class="step-icon">🔎</div>
          <div class="step-body">
            <div class="step-title">Step 2 — Pattern Analysis</div>
            <div class="step-desc">
              An AI reads every trade and asks: what did the winning trades have in common?
              What caused the losses? Were we buying too late? Did a specific sector hurt us?
              Was our stop-loss too tight or too wide? This produces a plain-English diagnosis.
            </div>
          </div>
        </div>
        <div class="flow-arrow">↓</div>

        <div class="flow-step">
          <div class="step-icon">⚙️</div>
          <div class="step-body">
            <div class="step-title">Step 3 — Strategy Evolution <span class="conditional-tag">only if we lagged SPY</span></div>
            <div class="step-desc">
              If we beat the S&amp;P 500 — nothing changes, the strategy is working.
              If we underperformed — an AI uses the pattern analysis to make targeted improvements:
              it adjusts numeric parameters (stop-loss %, position size, confidence threshold)
              AND rewrites specific parts of the instructions given to the Market Analyst and
              Paper Trader. A new strategy version is created and activated automatically.
            </div>
          </div>
        </div>
        <div class="flow-arrow">↓</div>

        <div class="flow-step highlight-step">
          <div class="step-icon">📄</div>
          <div class="step-body">
            <div class="step-title">Step 4 — Monthly Report &amp; Notification</div>
            <div class="step-desc">
              A PDF report is generated with the full month's results, the pattern analysis,
              and a summary of any strategy changes. You receive an in-app notification
              with the headline numbers.
            </div>
          </div>
        </div>
      </div>

      <div class="output-box retro-output">
        <span class="output-label">Output</span>
        Monthly PDF report, and (if SPY was beaten) a new active strategy version with tuned parameters and updated AI prompts.
      </div>
    </section>

    <!-- ── Key concepts ───────────────────────────────────────── -->
    <section class="concepts">
      <h3 class="concepts-title">Key Concepts</h3>
      <div class="concepts-grid">
        <div class="concept-card">
          <div class="concept-icon">💵</div>
          <div class="concept-name">Buying Power</div>
          <div class="concept-desc">
            Your available cash to invest, starting at $5,000. It goes down when you buy and up when
            you sell. Profits compound — a good month means more capital to deploy next month.
          </div>
        </div>
        <div class="concept-card">
          <div class="concept-icon">🛑</div>
          <div class="concept-name">Stop-Loss</div>
          <div class="concept-desc">
            A safety net. If a stock falls 10% below your buy price, it's automatically sold
            to prevent a bigger loss. Protects your capital on bad trades.
          </div>
        </div>
        <div class="concept-card">
          <div class="concept-icon">🎯</div>
          <div class="concept-name">Profit Target</div>
          <div class="concept-desc">
            The price at which the system takes profit. If a stock hits its target, it's sold
            automatically to lock in gains before the price can reverse.
          </div>
        </div>
        <div class="concept-card">
          <div class="concept-icon">📉</div>
          <div class="concept-name">S&amp;P 500 Benchmark</div>
          <div class="concept-desc">
            The S&amp;P 500 (SPY) is the performance yardstick. Historically it returns ~10% per year.
            Every decision the system makes is evaluated against this baseline — beating it is the goal.
          </div>
        </div>
        <div class="concept-card">
          <div class="concept-icon">🔒</div>
          <div class="concept-name">Paper Trading</div>
          <div class="concept-desc">
            Trades are simulated — no real money moves. This lets the strategy be tested and
            refined with real market data before any real capital is put at risk.
          </div>
        </div>
        <div class="concept-card">
          <div class="concept-icon">🔄</div>
          <div class="concept-name">Self-Improvement</div>
          <div class="concept-desc">
            The strategy is never static. The Retrospective Agent reads the results each month
            and rewrites the AI instructions when performance lags. The system learns from its mistakes.
          </div>
        </div>
      </div>
    </section>

  </div>
</template>

<style scoped>
.hiw { max-width: 860px; margin: 0 auto; }

/* Hero */
.hero { text-align: center; margin-bottom: 32px; }
.hero-title { font-size: 1.6rem; font-weight: 800; color: #1e3a5f; margin-bottom: 10px; }
.hero-sub { font-size: 0.95rem; color: #6b7280; line-height: 1.7; max-width: 620px; margin: 0 auto; }

/* Overview row */
.overview-row {
  display: flex; align-items: center; justify-content: center;
  gap: 12px; margin-bottom: 10px; flex-wrap: wrap;
}
.ov-agent {
  text-align: center; padding: 16px 24px; border-radius: 12px;
  min-width: 130px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.analyst  { background: #eff6ff; border: 2px solid #bfdbfe; }
.trader   { background: #f0fdf4; border: 2px solid #bbf7d0; }
.retro    { background: #faf5ff; border: 2px solid #e9d5ff; }
.ov-icon  { font-size: 1.8rem; margin-bottom: 6px; }
.ov-name  { font-weight: 700; font-size: 0.85rem; color: #1e3a5f; }
.ov-time  { font-size: 0.72rem; color: #9ca3af; margin-top: 3px; }
.ov-arrow { font-size: 1.5rem; color: #9ca3af; }
.overview-caption {
  text-align: center; font-size: 0.78rem; color: #9ca3af; margin-bottom: 36px;
}

/* Agent sections */
.agent-section {
  border-radius: 16px; padding: 28px; margin-bottom: 28px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.07);
}
.analyst-theme { background: #fff; border: 2px solid #bfdbfe; }
.trader-theme  { background: #fff; border: 2px solid #bbf7d0; }
.retro-theme   { background: #fff; border: 2px solid #e9d5ff; }

.agent-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
.agent-badge  { padding: 3px 10px; border-radius: 20px; font-size: 0.72rem; font-weight: 700; }
.analyst-badge { background: #dbeafe; color: #1d4ed8; }
.trader-badge  { background: #dcfce7; color: #15803d; }
.retro-badge   { background: #ede9fe; color: #7c3aed; }
.agent-title   { font-size: 1.15rem; font-weight: 800; color: #1e3a5f; margin: 0; }
.schedule-pill {
  margin-left: auto; font-size: 0.72rem; color: #6b7280;
  background: #f3f4f6; padding: 3px 10px; border-radius: 20px; white-space: nowrap;
}
.agent-desc { font-size: 0.875rem; color: #6b7280; line-height: 1.7; margin-bottom: 22px; }

/* Flow steps */
.flow { display: flex; flex-direction: column; gap: 0; }
.flow-step {
  display: flex; gap: 16px; align-items: flex-start;
  background: #f9fafb; border-radius: 10px; padding: 16px;
}
.highlight-step { background: #f0f9ff; border: 1px solid #bae6fd; }
.flow-arrow { text-align: center; color: #9ca3af; font-size: 1.2rem; padding: 4px 0; }
.step-icon  { font-size: 1.5rem; flex-shrink: 0; margin-top: 1px; }
.step-title { font-weight: 700; font-size: 0.88rem; color: #1e3a5f; margin-bottom: 5px; }
.step-desc  { font-size: 0.82rem; color: #6b7280; line-height: 1.65; }
.conditional-tag {
  background: #fef3c7; color: #92400e; font-size: 0.68rem;
  padding: 1px 7px; border-radius: 10px; font-weight: 500;
  vertical-align: middle; margin-left: 6px;
}

/* Output boxes */
.output-box {
  margin-top: 16px; border-radius: 8px; padding: 12px 16px;
  font-size: 0.82rem; line-height: 1.5; display: flex; align-items: flex-start; gap: 10px;
}
.analyst-output { background: #eff6ff; color: #1e40af; }
.trader-output  { background: #f0fdf4; color: #15803d; }
.retro-output   { background: #faf5ff; color: #6b21a8; }
.output-label {
  font-weight: 700; font-size: 0.7rem; padding: 2px 8px; border-radius: 4px;
  background: rgba(0,0,0,0.08); white-space: nowrap; flex-shrink: 0;
}

/* Key concepts */
.concepts { margin-top: 8px; }
.concepts-title { font-size: 1.1rem; font-weight: 800; color: #1e3a5f; margin-bottom: 16px; }
.concepts-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 14px; }
.concept-card {
  background: #fff; border-radius: 12px; padding: 18px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06); border: 1px solid #f3f4f6;
}
.concept-icon { font-size: 1.6rem; margin-bottom: 8px; }
.concept-name { font-weight: 700; font-size: 0.88rem; color: #1e3a5f; margin-bottom: 6px; }
.concept-desc { font-size: 0.8rem; color: #6b7280; line-height: 1.6; }

@media (max-width: 767px) {
  .agent-section { padding: 18px 14px; }
  .hero-title { font-size: 1.25rem; }
  .schedule-pill { margin-left: 0; }
  .ov-agent { padding: 12px 16px; min-width: 100px; }
  .concepts-grid { grid-template-columns: 1fr 1fr; }
}
</style>
