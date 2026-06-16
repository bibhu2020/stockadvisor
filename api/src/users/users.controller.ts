import { Controller, Get, Param, Patch, Body, UseGuards, ForbiddenException, Request } from '@nestjs/common';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { UsersService } from './users.service';

@Controller('users')
@UseGuards(JwtAuthGuard)
export class UsersController {
  constructor(private svc: UsersService) {}

  @Get()
  findAll(@Request() req: { user: { role: string } }) {
    if (req.user.role !== 'admin') throw new ForbiddenException();
    return this.svc.findAll();
  }

  @Patch(':id/approve')
  approve(@Param('id') id: string, @Request() req: { user: { role: string } }) {
    if (req.user.role !== 'admin') throw new ForbiddenException();
    return this.svc.approve(+id);
  }

  @Patch(':id/role')
  setRole(
    @Param('id') id: string,
    @Body() body: { role: string },
    @Request() req: { user: { role: string } },
  ) {
    if (req.user.role !== 'admin') throw new ForbiddenException();
    return this.svc.setRole(+id, body.role);
  }
}
