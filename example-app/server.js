const express = require("express");
const bodyParser = require("body-parser");
const cors = require("cors");
require("dotenv").config();

const authRoutes = require("./routes/auth");
const userRoutes = require("./routes/users");
const profileRoutes = require("./routes/profiles");
const documentRoutes = require("./routes/documents");
const orderRoutes = require("./routes/orders");
const messageRoutes = require("./routes/messages");

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// Routes
app.use("/api/auth", authRoutes);
app.use("/api/users", userRoutes);
app.use("/api/profiles", profileRoutes);
app.use("/api/documents", documentRoutes);
app.use("/api/orders", orderRoutes);
app.use("/api/messages", messageRoutes);

// Root endpoint
app.get("/", (req, res) => {
    res.json({
        message: "IDOR Vulnerable API - For Testing Purposes Only",
        warning: "This API contains intentional security vulnerabilities",
        endpoints: {
            auth: {
                register: "POST /api/auth/register",
                login: "POST /api/auth/login",
            },
            users: {
                list: "GET /api/users (requires auth)",
                getUser: "GET /api/users/:id (VULNERABLE - IDOR)",
                updateUser: "PUT /api/users/:id (VULNERABLE - IDOR)",
                deleteUser: "DELETE /api/users/:id (VULNERABLE - IDOR)",
            },
            profiles: {
                getProfile: "GET /api/profiles/:id (VULNERABLE - IDOR)",
                updateProfile: "PUT /api/profiles/:id (VULNERABLE - IDOR)",
            },
            documents: {
                list: "GET /api/documents (requires auth)",
                getDocument: "GET /api/documents/:id (VULNERABLE - IDOR)",
                createDocument: "POST /api/documents (requires auth)",
                updateDocument: "PUT /api/documents/:id (VULNERABLE - IDOR)",
                deleteDocument: "DELETE /api/documents/:id (VULNERABLE - IDOR)",
            },
            orders: {
                getOrder: "GET /api/orders/:id (VULNERABLE - IDOR)",
                updateOrder: "PUT /api/orders/:id (VULNERABLE - IDOR)",
                cancelOrder: "DELETE /api/orders/:id (VULNERABLE - IDOR)",
            },
            messages: {
                getMessage: "GET /api/messages/:id (VULNERABLE - IDOR)",
                deleteMessage: "DELETE /api/messages/:id (VULNERABLE - IDOR)",
            },
        },
    });
});

// Error handling middleware
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).json({ error: "Something went wrong!" });
});

app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
    console.log(`Access the API at http://localhost:${PORT}`);
    console.log("\n⚠️  WARNING: This API contains intentional IDOR vulnerabilities for testing purposes only!");
});
