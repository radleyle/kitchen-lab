# ALB = the front door. Path rules send /docs, /agent, ... to the backend
# and everything else to the Next.js frontend.

resource "aws_lb" "main" {
  name               = "${var.project}-${var.environment}"
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id
}

resource "aws_lb_target_group" "backend" {
  name        = "${var.project}-backend"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    matcher             = "200"
  }
}

resource "aws_lb_target_group" "frontend" {
  name        = "${var.project}-frontend"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    matcher             = "200-399"
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

locals {
  # Keep in sync when you add FastAPI routers.
  api_path_patterns = [
    "/health*",
    "/docs*",
    "/openapi.json",
    "/redoc*",
    "/auth*",
    "/agent*",
    "/assistant*",
    "/calculators*",
    "/diagnose*",
    "/recipes*",
    "/substitute*",
    "/kitchen*",
    "/knowledge*",
    "/safety*",
    "/techniques*",
    "/experiments*",
    "/notebook*",
    "/attachments*",
  ]
}

resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  condition {
    path_pattern {
      values = local.api_path_patterns
    }
  }
}
