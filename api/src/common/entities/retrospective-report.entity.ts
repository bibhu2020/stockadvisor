import {
  Column,
  CreateDateColumn,
  Entity,
  PrimaryGeneratedColumn,
} from 'typeorm';

@Entity('retrospective_reports')
export class RetrospectiveReport {
  @PrimaryGeneratedColumn() id: number;
  @Column() year: number;
  @Column() month: number;
  @Column({ nullable: true }) agent_run_id: number;
  @Column({ nullable: true }) old_strategy_id: number;
  @Column({ nullable: true }) new_strategy_id: number;
  @Column({ default: 0 }) total_trades: number;
  @Column({ default: 0 }) wins: number;
  @Column({ default: 0 }) losses: number;
  @Column('real', { default: 0 }) win_rate_pct: number;
  @Column('real', { default: 0 }) total_pnl: number;
  @Column('real', { nullable: true }) initial_value: number;
  @Column('real', { nullable: true }) spy_return_pct: number;
  @Column('real', { nullable: true }) spy_equivalent_pnl: number;
  @Column({ default: false }) underperformed_spy: boolean;
  @Column('text', { nullable: true }) patterns: string; // JSON
  @Column('text', { nullable: true }) tuning_rationale: string;
  @Column({ nullable: true }) prompts_updated: number;
  @Column({ nullable: true }) pdf_path: string;
  @CreateDateColumn() created_at: Date;

  getPatterns(): Record<string, unknown> {
    try {
      return this.patterns ? JSON.parse(this.patterns) : {};
    } catch {
      return {};
    }
  }
}
