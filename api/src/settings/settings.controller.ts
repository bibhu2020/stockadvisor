import { Body, Controller, ForbiddenException, Get, Patch, Request, UseGuards } from '@nestjs/common';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { SettingsService } from './settings.service';

@Controller('settings')
@UseGuards(JwtAuthGuard)
export class SettingsController {
  constructor(private svc: SettingsService) {}

  @Get()
  findAll() { return this.svc.findAll(); }

  @Patch()
  update(@Body() body: Record<string, string>, @Request() req: { user: { role: string } }) {
    if (req.user.role !== 'admin') throw new ForbiddenException();
    return this.svc.update(body);
  }
}
