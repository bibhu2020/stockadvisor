import { Column, CreateDateColumn, Entity, PrimaryGeneratedColumn } from 'typeorm';

@Entity('agent_runs')
export class AgentRun {
  @PrimaryGeneratedColumn() id: number;
  @Column() agent_type: string;
  @Column({ default: 'pending' }) status: string;
  @Column({ nullable: true }) started_at: Date;
  @Column({ nullable: true }) finished_at: Date;
  @Column('text', { default: '' }) log: string;
  @Column('text', { nullable: true }) error: string;
  @Column({ default: 'scheduler' }) triggered_by: string;
}
