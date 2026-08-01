const mongoose = require('mongoose');

const NoteSchema = mongoose.Schema({
    title: String,
    content: String,
    tags: [String],
    categories: [String],
    folder: String
}, {
    timestamps: true
});

module.exports = mongoose.model('Note', NoteSchema);