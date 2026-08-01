const mongoose = require('mongoose');

const NoteSchema = mongoose.Schema({
            title: String,
            content: String,
            priority: String,
    tags: [String],
            categories: [String],
            folder: String,
            color: String
}, {
    timestamps: true
});

module.exports = mongoose.model('Note', NoteSchema);