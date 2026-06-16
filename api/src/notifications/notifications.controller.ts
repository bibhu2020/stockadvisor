import { Controller, Get, Param, Patch, Request, UseGuards } from '@nestjs/common';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { NotificationsService } from './notifications.service';

@Controller('notifications')
@UseGuards(JwtAuthGuard)
export class NotificationsController {
  constructor(private svc: NotificationsService) {}

  @Get()
  findAll(@Request() req: { user: { id: number } }) {
    return this.svc.findForUser(req.user.id);
  }

  @Get('unread-count')
  unreadCount(@Request() req: { user: { id: number } }) {
    return this.svc.unreadCount(req.user.id);
  }

  @Patch(':id/read')
  markRead(@Param('id') id: string, @Request() req: { user: { id: number } }) {
    return this.svc.markRead(+id, req.user.id);
  }

  @Patch('read-all')
  markAllRead(@Request() req: { user: { id: number } }) {
    return this.svc.markAllRead(req.user.id);
  }
}
