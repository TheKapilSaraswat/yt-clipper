import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import mongoose from "mongoose";
import waitlistRoutes from "./routes/waitlist.js";
import analyticsRoutes from "./routes/analytics.js";

dotenv.config();

const app = express();
app.use(cors({ origin: process.env.CLIENT_URL || "*" }));
app.use(express.json());

mongoose.connect(process.env.MONGODB_URI)
  .then(() => console.log("MongoDB connected"))
  .catch((err) => console.error("MongoDB error:", err));

app.use("/api/waitlist", waitlistRoutes);
app.use("/api/analytics", analyticsRoutes);

app.get("/api/health", (_, res) => res.json({ ok: true }));

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
