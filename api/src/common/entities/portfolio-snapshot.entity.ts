import { Column, CreateDateColumn, Entity, PrimaryGeneratedColumn } from 'typeorm';

@Entity('portfolio_snapshots')
export class PortfolioSnapshot {
  @PrimaryGeneratedColumn() id: number;
  @CreateDateColumn() snapshot_at: Date;
  @Column('real') buying_power: number;
  @Column('real', { default: 0 }) open_positions_value: number;
  @Column('real') total_value: number;
  @Column({ nullable: true }) agent_run_id: number;
}
