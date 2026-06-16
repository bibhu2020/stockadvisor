import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Between, Repository } from 'typeorm';
import { Transaction } from '../common/entities/transaction.entity';

@Injectable()
export class TransactionsService {
  constructor(@InjectRepository(Transaction) private repo: Repository<Transaction>) {}

  async findAll(filters: {
    symbol?: string;
    action?: string;
    from?: string;
    to?: string;
    strategy_id?: string;
    pnl?: 'gain' | 'loss' | 'all';
  }) {
    const qb = this.repo
      .createQueryBuilder('t')
      .leftJoin('positions', 'p', 'p.id = t.position_id')
      .addSelect('p.entry_price',       'pos_entry_price')
      .addSelect('p.exit_target_price', 'pos_exit_target_price')
      .addSelect('p.stop_loss_price',   'pos_stop_loss_price')
      .addSelect('p.status',            'pos_status')
      .addSelect('p.close_reason',      'pos_close_reason')
      .orderBy('t.executed_at', 'DESC')
      .take(500);

    if (filters.symbol)      qb.andWhere('t.symbol = :sym',    { sym: filters.symbol.toUpperCase() });
    if (filters.action)      qb.andWhere('t.action = :action', { action: filters.action });
    if (filters.strategy_id) qb.andWhere('t.strategy_id = :sid', { sid: +filters.strategy_id });
    if (filters.from)        qb.andWhere('t.executed_at >= :from', { from: filters.from });
    if (filters.to)          qb.andWhere('t.executed_at <= :to',   { to: filters.to });
    if (filters.pnl === 'gain') qb.andWhere('t.realized_pnl > 0');
    if (filters.pnl === 'loss') qb.andWhere('t.realized_pnl <= 0');

    const raw = await qb.getRawAndEntities();

    // Merge position fields onto each transaction entity
    return raw.entities.map((tx, i) => ({
      ...tx,
      pos_entry_price:       raw.raw[i]?.pos_entry_price       ?? null,
      pos_exit_target_price: raw.raw[i]?.pos_exit_target_price ?? null,
      pos_stop_loss_price:   raw.raw[i]?.pos_stop_loss_price   ?? null,
      pos_status:            raw.raw[i]?.pos_status            ?? null,
      pos_close_reason:      raw.raw[i]?.pos_close_reason      ?? null,
    }));
  }

  async getMarketPrices(symbols: string[]): Promise<Record<string, number | null>> {
    if (!symbols.length) return {};
    const unique = [...new Set(symbols.map((s) => s.toUpperCase()))];

    const fetchOne = async (sym: string): Promise<[string, number | null]> => {
      try {
        const url = `https://query1.finance.yahoo.com/v8/finance/chart/${sym}?interval=1d&range=1d`;
        const res = await fetch(url, {
          headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' },
          signal: AbortSignal.timeout(8000),
        });
        if (!res.ok) return [sym, null];
        const json: any = await res.json();
        const price: number | null = json?.chart?.result?.[0]?.meta?.regularMarketPrice ?? null;
        return [sym, price];
      } catch {
        return [sym, null];
      }
    };

    const results = await Promise.all(unique.map(fetchOne));
    return Object.fromEntries(results);
  }

  async summary() {
    const sells = await this.repo.find({ where: { action: 'SELL' } });
    const wins = sells.filter((t) => (t.realized_pnl ?? 0) > 0);
    const total_pnl = sells.reduce((acc, t) => acc + (t.realized_pnl ?? 0), 0);
    return {
      total_trades: sells.length,
      wins: wins.length,
      losses: sells.length - wins.length,
      win_rate_pct: sells.length ? +((wins.length / sells.length) * 100).toFixed(1) : 0,
      total_pnl: +total_pnl.toFixed(2),
    };
  }
}
