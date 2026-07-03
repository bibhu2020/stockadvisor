import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { RetrospectiveReport } from '../common/entities/retrospective-report.entity';

@Injectable()
export class RetrospectiveReportsService {
  constructor(
    @InjectRepository(RetrospectiveReport)
    private repo: Repository<RetrospectiveReport>,
  ) {}

  findAll() {
    return this.repo.find({ order: { created_at: 'DESC' }, take: 60 });
  }

  async findOne(id: number) {
    const r = await this.repo.findOne({ where: { id } });
    if (!r) throw new NotFoundException();
    return r;
  }

  async getPdfPath(id: number): Promise<string> {
    const r = await this.repo.findOne({ where: { id } });
    if (!r || !r.pdf_path) throw new NotFoundException('PDF not found');
    return r.pdf_path;
  }
}
