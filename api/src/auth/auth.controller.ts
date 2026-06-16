import { Body, Controller, Get, Patch, Post, Request, SetMetadata, UseGuards } from '@nestjs/common';
import { IS_PUBLIC_KEY, JwtAuthGuard } from './jwt-auth.guard';
import { AuthService } from './auth.service';

@Controller('auth')
export class AuthController {
  constructor(private auth: AuthService) {}

  @SetMetadata(IS_PUBLIC_KEY, true)
  @Post('register')
  register(@Body() body: { email: string; name: string; password: string }) {
    return this.auth.register(body.email, body.name, body.password);
  }

  @SetMetadata(IS_PUBLIC_KEY, true)
  @Post('login')
  login(@Body() body: { email: string; password: string }) {
    return this.auth.login(body.email, body.password);
  }

  @UseGuards(JwtAuthGuard)
  @Get('me')
  me(@Request() req: { user: { id: number } }) {
    return this.auth.me(req.user.id);
  }

  @UseGuards(JwtAuthGuard)
  @Patch('profile')
  updateProfile(
    @Request() req: { user: { id: number } },
    @Body() body: { name: string },
  ) {
    return this.auth.updateProfile(req.user.id, body.name);
  }

  @UseGuards(JwtAuthGuard)
  @Patch('password')
  changePassword(
    @Request() req: { user: { id: number } },
    @Body() body: { currentPassword: string; newPassword: string },
  ) {
    return this.auth.changePassword(req.user.id, body.currentPassword, body.newPassword);
  }
}
