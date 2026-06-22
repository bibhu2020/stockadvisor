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
    const sells = await this.txRepo.find({ where: { action: 'SELL' }, order: { executed_at: 'ASC' } });
    const byMonth: Record<string, { realized_pnl: number }> = {};
    for (const tx of sells) {
      const key = tx.executed_at.toISOString().slice(0, 7); // YYYY-MM
      if (!byMonth[key]) byMonth[key] = { realized_pnl: 0 };
      byMonth[key].realized_pnl += tx.realized_pnl ?? 0;
    }
    return Object.entries(byMonth).map(([month, v]) => ({
      month,
      realized_pnl: +v.realized_pnl.toFixed(2),
    }));
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
