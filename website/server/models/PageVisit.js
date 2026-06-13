import mongoose from "mongoose";

const pageVisitSchema = new mongoose.Schema({
  source: { type: String, default: "direct" },
  referralCode: { type: String, default: null },
  ip: { type: String, default: "" },
  userAgent: { type: String, default: "" },
  signedUp: { type: Boolean, default: false },
  createdAt: { type: Date, default: Date.now },
});

export default mongoose.model("PageVisit", pageVisitSchema);
