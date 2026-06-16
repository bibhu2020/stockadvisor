import { Column, CreateDateColumn, Entity, PrimaryGeneratedColumn } from 'typeorm';

@Entity('strategies')
export class Strategy {
  @PrimaryGeneratedColumn() id: number;
  @Column() version: number;
  @Column() name: string;
  @Column('text') description: string;
  @Column('text') parameters: string; // JSON
  @Column({ default: false }) is_active: boolean;
  @Column('real', { nullable: true }) performance_vs_spy: number;
  @Column({ default: 'initial' }) source: string;
  @CreateDateColumn() created_at: Date;

  getParameters(): Record<string, unknown> {
    try { return JSON.parse(this.parameters); } catch { return {}; }
  }
}
