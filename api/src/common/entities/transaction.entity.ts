import { Column, CreateDateColumn, Entity, JoinColumn, ManyToOne, PrimaryGeneratedColumn } from 'typeorm';
import { Position } from './position.entity';

@Entity('transactions')
export class Transaction {
  @PrimaryGeneratedColumn() id: number;
  @Column() symbol: string;
  @Column() action: string; // BUY | SELL | HOLD
  @Column('real') price: number;
  @Column() quantity: number;
  @Column('real') amount: number;
  @Column({ nullable: true }) position_id: number;
  @Column({ nullable: true }) strategy_id: number;
  @Column({ nullable: true }) agent_run_id: number;
  @Column('text', { nullable: true }) reason: string;
  @Column('real', { nullable: true }) realized_pnl: number;
  @CreateDateColumn() executed_at: Date;
  @ManyToOne(() => Position, (p) => p.transactions, { nullable: true })
  @JoinColumn({ name: 'position_id' })
  position: Position;
}
