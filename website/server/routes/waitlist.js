import { Router } from "express";
import { v4 as uuidv4 } from "uuid";
import WaitlistUser from "../models/WaitlistUser.js";
import PageVisit from "../models/PageVisit.js";
import { sendConfirmationEmail } from "../utils/email.js";

const router = Router();

router.post("/signup", async (req, res) => {
  try {
    const { name, email, niche, goal, referredBy } = req.body;
    if (!name || !email) {
      return res.status(400).json({ error: "Name and email are required" });
    }

    const exists = await WaitlistUser.findOne({ email });
    if (exists) {
      return res.status(409).json({ error: "This email is already on the waitlist" });
    }

    const count = await WaitlistUser.countDocuments();
    const referralCode = uuidv4().slice(0, 8);

    const user = await WaitlistUser.create({
      name,
      email,
      niche: niche || "",
      goal: goal || "",
      referralCode,
      referredBy: referredBy || null,
      position: count + 1,
    });

    if (referredBy) {
      await WaitlistUser.findOneAndUpdate(
        { referralCode: referredBy },
        { $inc: { referralCount: 1 } }
      );
    }

    await PageVisit.updateMany(
      { ip: req.headers["x-forwarded-for"]?.split(",")[0]?.trim() || req.ip || "" },
      { signedUp: true }
    ).catch(() => {});

    try {
      await sendConfirmationEmail(email, name, user.position);
    } catch (err) {
      console.error("Email send failed:", err.message);
    }

    res.status(201).json({
      message: "You're on the waitlist!",
      position: user.position,
      referralCode: user.referralCode,
    });
  } catch (err) {
    console.error("Signup error:", err);
    res.status(500).json({ error: "Something went wrong" });
  }
});

router.get("/position/:email", async (req, res) => {
  try {
    const user = await WaitlistUser.findOne({ email: req.params.email });
    if (!user) return res.status(404).json({ error: "Not found" });
    res.json({ position: user.position, referralCode: user.referralCode });
  } catch (err) {
    res.status(500).json({ error: "Something went wrong" });
  }
});

router.get("/ref/:code", async (req, res) => {
  try {
    const user = await WaitlistUser.findOne({ referralCode: req.params.code });
    if (!user) return res.status(404).json({ error: "Invalid referral code" });
    res.redirect(`${process.env.CLIENT_URL || "http://localhost:5173"}?ref=${req.params.code}`);
  } catch (err) {
    res.status(500).json({ error: "Something went wrong" });
  }
});

router.post("/visit", async (req, res) => {
  try {
    const ip = req.headers["x-forwarded-for"]?.split(",")[0]?.trim() || req.ip || "";
    await PageVisit.create({
      source: req.body.source || "direct",
      referralCode: req.body.ref || null,
      ip,
      userAgent: req.headers["user-agent"] || "",
    });
    res.json({ ok: true });
  } catch {
    res.status(500).json({ error: "Something went wrong" });
  }
});

export default router;
