# -*- coding: utf-8 -*-
from flask.ext.mail import Message
from flask import render_template, current_app
from . import mail


def send_email(to, subject, template, **kwargs):
    msg = Message(subject, sender=current_app.config['FLASKY_MAIL_SENDER'], recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs) #??参数怎么写 'Flasky Admin <13675157322@163.com>'
    msg.html = render_template(template + '.html', **kwargs)
    mail.send(msg)