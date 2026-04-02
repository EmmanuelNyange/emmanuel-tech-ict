const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

// Connect to MongoDB
mongoose.connect('mongodb://127.0.0.1:27017/emmanuelTechDB')
.then(() => console.log("Connected to MongoDB"))
.catch(err => console.log(err));

// Schema
const bookingSchema = new mongoose.Schema({
    name: String,
    phone: String,
    problem: String,
    date: { type: Date, default: Date.now }
});

const Booking = mongoose.model('Booking', bookingSchema);

// Save booking
app.post('/book', async (req, res) => {
    const { name, phone, problem } = req.body;

    const newBooking = new Booking({ name, phone, problem });
    await newBooking.save();

    res.json({ message: "Booking saved successfully" });
});

// Get all bookings (Admin)
app.get('/bookings', async (req, res) => {
    const bookings = await Booking.find().sort({ date: -1 });
    res.json(bookings);
});

app.listen(3000, () => console.log("Server running on port 3000"));