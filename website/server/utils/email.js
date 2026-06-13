import nodemailer from "nodemailer";

const transporter = nodemailer.createTransport({
  host: process.env.EMAIL_HOST,
  port: parseInt(process.env.EMAIL_PORT),
  secure: false,
  auth: {
    user: process.env.EMAIL_USER,
    pass: process.env.EMAIL_PASS,
  },
});

export async function sendConfirmationEmail(email, name, position) {
  await transporter.sendMail({
    from: `"YT Clipper Waitlist" <${process.env.EMAIL_USER}>`,
    to: email,
    subject: "You're on the waitlist!",
    html: `<h2>Hey ${name},</h2>
<p>You're <strong>#${position}</strong> on the YT Clipper waitlist.</p>
<p>We'll keep you posted on our progress. Stay tuned!</p>
<p>– YT Clipper Team</p>`,
  });
}

export async function sendUpdateEmail(email, name) {
  await transporter.sendMail({
    from: `"YT Clipper Waitlist" <${process.env.EMAIL_USER}>`,
    to: email,
    subject: "What we're building at YT Clipper",
    html: `<h2>Hey ${name},</h2>
<p>We're building an automated YouTube Shorts pipeline that discovers trending content, clips it, and uploads it — all on autopilot.</p>
<p>More updates coming soon!</p>
<p>– YT Clipper Team</p>`,
  });
}

export async function sendBetaInviteEmail(email, name) {
  await transporter.sendMail({
    from: `"YT Clipper Waitlist" <${process.env.EMAIL_USER}>`,
    to: email,
    subject: "You're invited to the YT Clipper beta!",
    html: `<h2>Hey ${name},</h2>
<p>The beta is live and <strong>you're invited!</strong></p>
<p>Check your dashboard to get started.</p>
<p>– YT Clipper Team</p>`,
  });
}
