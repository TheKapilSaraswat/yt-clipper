import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import mongoose from "mongoose";
import path from "path";
import { fileURLToPath } from "url";
import waitlistRoutes from "./routes/waitlist.js";
import analyticsRoutes from "./routes/analytics.js";

dotenv.config();

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const app = express();
app.use(cors({ origin: process.env.CLIENT_URL || "*" }));
app.use(express.json());

mongoose.connect(process.env.MONGODB_URI)
  .then(() => console.log("MongoDB connected"))
  .catch((err) => console.error("MongoDB error:", err));

app.use("/api/waitlist", waitlistRoutes);
app.use("/api/analytics", analyticsRoutes);

app.get("/api/health", (_, res) => res.json({ ok: true }));

const clientDist = path.resolve(__dirname, "../client/dist");
app.use(express.static(clientDist));
app.get("*", (_, res) => res.sendFile(path.join(clientDist, "index.html")));

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
