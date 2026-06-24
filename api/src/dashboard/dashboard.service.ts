import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Transaction } from '../common/entities/transaction.entity';
import { PortfolioSnapshot } from '../common/entities/portfolio-snapshot.entity';
import { AgentRunsService } from '../agent-runs/agent-runs.service';

@Injectable()
export class DashboardService {
  constructor(
    @InjectRepository(Transaction) private txRepo: Repository<Transaction>,
    @InjectRepository(PortfolioSnapshot) private snapRepo: Repository<PortfolioSnapshot>,
    private agentSvc: AgentRunsService,
  ) {}

  async monthlyPnl() {
    const INITIAL_CAPITAL = 5000;

    const sells = await this.txRepo.find({ where: { action: 'SELL' }, order: { executed_at: 'ASC' } });
    const byMonth: Record<string, { realized_pnl: number }> = {};
    for (const tx of sells) {
      const key = tx.executed_at.toISOString().slice(0, 7);
      if (!byMonth[key]) byMonth[key] = { realized_pnl: 0 };
      byMonth[key].realized_pnl += tx.realized_pnl ?? 0;
    }
    const months = Object.keys(byMonth).sort();
    if (!months.length) return [];

    // Portfolio cumulative % — use last snapshot per month (snapshots ordered ASC → later overwrites)
    const snaps = await this.snapRepo.find({ order: { snapshot_at: 'ASC' } });
    const snapByMonth: Record<string, number> = {};
    for (const snap of snaps) {
      snapByMonth[snap.snapshot_at.toISOString().slice(0, 7)] = snap.total_value;
    }
    const portfolioPctByMonth: Record<string, number | null> = {};
    for (const m of months) {
      const val = snapByMonth[m];
      portfolioPctByMonth[m] = val != null ? +((val - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100).toFixed(2) : null;
    }

    const spyPctByMonth = await this.fetchSpyMonthlyPcts(months);

    return months.map((month) => ({
      month,
      realized_pnl: +byMonth[month].realized_pnl.toFixed(2),
      portfolio_pct: portfolioPctByMonth[month] ?? null,
      spy_pct: spyPctByMonth[month] ?? null,
    }));
  }

  private async fetchSpyMonthlyPcts(months: string[]): Promise<Record<string, number | null>> {
    if (!months.length) return {};
    // Fetch from one month before the first month so that month's close is our baseline price
    const baseline = new Date(months[0] + '-01');
    baseline.setUTCMonth(baseline.getUTCMonth() - 1);
    const period1 = Math.floor(baseline.getTime() / 1000);
    const period2 = Math.floor(Date.now() / 1000);
    try {
      const res = await fetch(
        `https://query1.finance.yahoo.com/v8/finance/chart/SPY?interval=1mo&period1=${period1}&period2=${period2}`,
        { headers: { 'User-Agent': 'stockadvisor/1.0' } },
      );
      const json: any = await res.json();
      const result = json?.chart?.result?.[0];
      if (!result) return {};
      const timestamps: number[] = result.timestamp;
      const closes: number[] = result.indicators.quote[0].close;
      const basePrice = closes[0]; // end-of-month price before our tracking period
      const out: Record<string, number | null> = {};
      for (let i = 1; i < timestamps.length; i++) {
        if (closes[i] == null) continue;
        const d = new Date(timestamps[i] * 1000);
        const m = `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}`;
        out[m] = +((closes[i] - basePrice) / basePrice * 100).toFixed(2);
      }
      return out;
    } catch {
      return {};
    }
  }

  async portfolioHistory() {
    const snaps = await this.snapRepo.find({ order: { snapshot_at: 'ASC' }, take: 200 });
    if (!snaps.length) return [];

    const sells = await this.txRepo.find({
      where: { action: 'SELL' },
      order: { executed_at: 'ASC' },
    });

    const INITIAL_CAPITAL = 5000;
    let cumRealized = 0;
    let si = 0;

    return snaps.map((snap) => {
      while (si < sells.length && +sells[si].executed_at <= +snap.snapshot_at) {
        cumRealized += sells[si].realized_pnl ?? 0;
        si++;
      }
      const realized_pnl = +cumRealized.toFixed(2);
      const unrealized_pnl = +(snap.total_value - INITIAL_CAPITAL - cumRealized).toFixed(2);
      return {
        snapshot_at: snap.snapshot_at,
        total_value: snap.total_value,
        realized_pnl,
        unrealized_pnl,
      };
    });
  }

  async winRate() {
    const sells = await this.txRepo.find({ where: { action: 'SELL' } });
    const wins = sells.filter((t) => (t.realized_pnl ?? 0) > 0);
    return {
      wins: wins.length,
      losses: sells.length - wins.length,
      win_rate_pct: sells.length ? +((wins.length / sells.length) * 100).toFixed(1) : 0,
    };
  }

  async sectorBreakdown() {
    // Group realized PnL by symbol (sector unavailable in transactions — group by symbol)
    const sells = await this.txRepo.find({ where: { action: 'SELL' } });
    const bySymbol: Record<string, number> = {};
    for (const tx of sells) {
      bySymbol[tx.symbol] = (bySymbol[tx.symbol] ?? 0) + (tx.realized_pnl ?? 0);
    }
    return Object.entries(bySymbol).map(([symbol, pnl]) => ({
      symbol,
      pnl: +pnl.toFixed(2),
    }));
  }

  agentStatus() {
    return this.agentSvc.lastRunByType();
  }
}
