import { Column, CreateDateColumn, Entity, PrimaryGeneratedColumn } from 'typeorm';

@Entity('analyst_reports')
export class AnalystReport {
  @PrimaryGeneratedColumn() id: number;
  @Column() report_date: string;
  @Column({ nullable: true }) agent_run_id: number;
  @Column('text') picks: string; // JSON
  @Column('text', { nullable: true }) market_summary: string;
  @Column('real', { nullable: true }) vix_level: number;
  @Column({ nullable: true }) pdf_path: string;
  @CreateDateColumn() created_at: Date;

  getPicks(): unknown[] {
    try { return JSON.parse(this.picks); } catch { return []; }
  }
}
