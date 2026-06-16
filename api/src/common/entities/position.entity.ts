import { Column, CreateDateColumn, Entity, OneToMany, PrimaryGeneratedColumn } from 'typeorm';
import { Transaction } from './transaction.entity';

@Entity('positions')
export class Position {
  @PrimaryGeneratedColumn() id: number;
  @Column() symbol: string;
  @Column({ nullable: true }) strategy_id: number;
  @Column({ nullable: true }) analyst_report_id: number;
  @Column('real') entry_price: number;
  @Column() quantity: number;
  @Column('real') cost_basis: number;
  @Column('real') stop_loss_price: number;
  @Column('real') exit_target_price: number;
  @Column({ default: 'open' }) status: string;
  @CreateDateColumn() opened_at: Date;
  @Column({ nullable: true }) closed_at: Date;
  @Column({ nullable: true }) close_reason: string;
  @OneToMany(() => Transaction, (t) => t.position) transactions: Transaction[];
}
