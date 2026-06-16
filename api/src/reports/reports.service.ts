import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { AnalystReport } from '../common/entities/analyst-report.entity';

@Injectable()
export class ReportsService {
  constructor(@InjectRepository(AnalystReport) private repo: Repository<AnalystReport>) {}

  findAll() {
    return this.repo.find({ order: { created_at: 'DESC' }, take: 60 });
  }

  async findOne(id: number) {
    const r = await this.repo.findOne({ where: { id } });
    if (!r) throw new NotFoundException();
    return r;
  }

  async getPdfPath(id: number): Promise<string> {
    const r = await this.repo.findOne({ where: { id }, select: { pdf_path: true } });
    if (!r || !r.pdf_path) throw new NotFoundException('PDF not found');
    return r.pdf_path;
  }
}
