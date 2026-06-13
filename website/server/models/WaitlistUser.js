import mongoose from "mongoose";

const waitlistUserSchema = new mongoose.Schema({
  name: { type: String, required: true },
  email: { type: String, required: true, unique: true },
  niche: { type: String, default: "" },
  goal: { type: String, default: "" },
  referralCode: { type: String, unique: true },
  referredBy: { type: String, default: null },
  referralCount: { type: Number, default: 0 },
  position: { type: Number },
  createdAt: { type: Date, default: Date.now },
});

export default mongoose.model("WaitlistUser", waitlistUserSchema);
