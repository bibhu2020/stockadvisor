import { Controller, Get, Param, UseGuards } from '@nestjs/common';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { StrategiesService } from './strategies.service';

@Controller('strategies')
@UseGuards(JwtAuthGuard)
export class StrategiesController {
  constructor(private svc: StrategiesService) {}
  @Get() findAll() { return this.svc.findAll(); }
  @Get('active') active() { return this.svc.active(); }
  @Get(':id') findOne(@Param('id') id: string) { return this.svc.findOne(+id); }
}
