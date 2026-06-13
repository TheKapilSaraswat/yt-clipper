import { Router } from "express";
import WaitlistUser from "../models/WaitlistUser.js";
import PageVisit from "../models/PageVisit.js";
import { requireAuth, login } from "../auth.js";

const router = Router();

router.post("/login", (req, res) => {
  const result = login(req.body.password);
  if (!result) {
    return res.status(401).json({ error: "Invalid password" });
  }
  res.json(result);
});

router.use(requireAuth);

router.get("/dashboard", async (req, res) => {
  try {
    const total = await WaitlistUser.countDocuments();
    const todayStart = new Date();
    todayStart.setHours(0, 0, 0, 0);
    const todaySignups = await WaitlistUser.countDocuments({ createdAt: { $gte: todayStart } });
    const referralSignups = await WaitlistUser.countDocuments({ referredBy: { $ne: null } });
    const totalVisits = await PageVisit.countDocuments();
    const uniqueVisitors = (await PageVisit.distinct("ip")).length;
    const linkClicks = await PageVisit.countDocuments({ referralCode: { $ne: null } });
    const signedUpVisitors = await PageVisit.countDocuments({ signedUp: true });
    const conversionRate = totalVisits > 0 ? ((total / totalVisits) * 100).toFixed(1) : "0.0";

    const users = await WaitlistUser.find().sort({ createdAt: -1 }).limit(200);

    const recentVisits = await PageVisit.find()
      .sort({ createdAt: -1 })
      .limit(50)
      .lean();

    res.json({
      total,
      todaySignups,
      referralSignups,
      totalVisits,
      uniqueVisitors,
      linkClicks,
      signedUpVisitors,
      conversionRate,
      users,
      recentVisits,
    });
  } catch (err) {
    console.error("Dashboard error:", err);
    res.status(500).json({ error: "Something went wrong" });
  }
});

router.get("/export", async (req, res) => {
  try {
    const users = await WaitlistUser.find().sort({ createdAt: -1 });
    const csv = [
      "Name,Email,Niche,Goal,Referral Code,Referred By,Referral Count,Position,Joined",
      ...users.map((u) =>
        `"${u.name}","${u.email}","${u.niche || ""}","${u.goal || ""}","${u.referralCode}","${u.referredBy || ""}",${u.referralCount},${u.position},"${u.createdAt.toISOString()}"`
      ),
    ].join("\n");
    res.setHeader("Content-Type", "text/csv");
    res.setHeader("Content-Disposition", "attachment; filename=waitlist.csv");
    res.send(csv);
  } catch (err) {
    res.status(500).json({ error: "Something went wrong" });
  }
});

router.delete("/user/:id", async (req, res) => {
  try {
    await WaitlistUser.findByIdAndDelete(req.params.id);
    res.json({ ok: true });
  } catch {
    res.status(500).json({ error: "Something went wrong" });
  }
});

router.get("/search", async (req, res) => {
  try {
    const q = req.query.q || "";
    const users = await WaitlistUser.find({
      $or: [
        { name: { $regex: q, $options: "i" } },
        { email: { $regex: q, $options: "i" } },
      ],
    }).sort({ createdAt: -1 }).limit(50);
    res.json(users);
  } catch {
    res.status(500).json({ error: "Something went wrong" });
  }
});

export default router;
