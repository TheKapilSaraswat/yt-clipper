import { v4 as uuidv4 } from "uuid";

const tokens = new Map();
const TOKEN_EXPIRY = 24 * 60 * 60 * 1000;

export function createToken() {
  const token = uuidv4();
  tokens.set(token, Date.now() + TOKEN_EXPIRY);
  return token;
}

export function requireAuth(req, res, next) {
  const token = req.headers.authorization?.replace("Bearer ", "") || req.query.token;
  if (!token || !tokens.has(token)) {
    return res.status(401).json({ error: "Unauthorized" });
  }
  if (tokens.get(token) < Date.now()) {
    tokens.delete(token);
    return res.status(401).json({ error: "Token expired" });
  }
  next();
}

export function login(password) {
  if (password === process.env.ADMIN_PASSWORD) {
    return { token: createToken() };
  }
  return null;
}