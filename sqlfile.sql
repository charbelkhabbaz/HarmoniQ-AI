DROP DATABASE IF EXISTS my_music_db;
CREATE DATABASE my_music_db;
use my_music_db;

-- -----------------------------------------------------------------------------------
-- MySQL Database Script for Music Intelligence Dataset
-- Generated from Python data model (40 Songs from 10 Core Lebanese Artists)
-- -----------------------------------------------------------------------------------

-- Configuration for safe execution
SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";
SET FOREIGN_KEY_CHECKS = 0; -- Temporarily disable FK checks for table drops/creation

-- Drop tables in reverse dependency order for a clean restart
DROP TABLE IF EXISTS recommendations_log;
DROP TABLE IF EXISTS user_requests;
DROP TABLE IF EXISTS lyric_translations;
DROP TABLE IF EXISTS audio_fingerprints;
DROP TABLE IF EXISTS music_notes;
DROP TABLE IF EXISTS song_features;
DROP TABLE IF EXISTS lyrics;
DROP TABLE IF EXISTS songs;
DROP TABLE IF EXISTS albums;
DROP TABLE IF EXISTS artists;

-- Re-enable FK checks
SET FOREIGN_KEY_CHECKS = 1;

-- -----------------------------------------------------------------------------------
-- 1. Table Definitions (DDL)
-- -----------------------------------------------------------------------------------

-- Artists Table: Core information about the musicians
CREATE TABLE artists (
    artist_id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    nationality VARCHAR(100),
    birth_year INT(4),
    description TEXT,
    spotify_id CHAR(22) UNIQUE,
    youtube_channel VARCHAR(255)
);

-- Albums Table: Information about the albums released
CREATE TABLE albums (
    album_id INT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    artist_id INT NOT NULL,
    release_year INT(4),
    cover_url VARCHAR(512),
    FOREIGN KEY (artist_id) REFERENCES artists(artist_id) ON DELETE CASCADE
);

-- Songs Table: Central table containing song metadata
CREATE TABLE songs (
    song_id INT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    artist_id INT NOT NULL,
    album_id INT NOT NULL,
    release_year INT(4),
    genre VARCHAR(100),
    bpm SMALLINT,
    key_signature VARCHAR(50),
    duration_seconds SMALLINT,
    mood VARCHAR(100),
    language VARCHAR(50),
    spotify_id CHAR(22) ,
    youtube_id CHAR(11) ,
    audio_url VARCHAR(512),
    FOREIGN KEY (artist_id) REFERENCES artists(artist_id) ON DELETE CASCADE,
    FOREIGN KEY (album_id) REFERENCES albums(album_id) ON DELETE CASCADE
);

-- Lyrics Table: Detailed lyrics content
CREATE TABLE lyrics (
    lyric_id INT PRIMARY KEY,
    song_id INT UNIQUE NOT NULL,
    lyric_text TEXT,
    language VARCHAR(50),
    source VARCHAR(100),
    FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
);

-- Song Features Table: Numerical audio analysis features (Spotify-style)
CREATE TABLE song_features (
    feature_id INT PRIMARY KEY,
    song_id INT UNIQUE NOT NULL,
    danceability FLOAT(5, 3), -- Range 0.0 to 1.0
    energy FLOAT(5, 3),
    valence FLOAT(5, 3),
    acousticness FLOAT(5, 3),
    instrumentalness FLOAT(5, 3),
    liveness FLOAT(5, 3),
    speechiness FLOAT(5, 3),
    mode TINYINT, -- 1=Major, 0=Minor
    loudness FLOAT(5, 2), -- dB
    FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
);

-- Music Notes Table: Technical music properties
CREATE TABLE music_notes (
    note_id INT PRIMARY KEY,
    song_id INT UNIQUE NOT NULL,
    midi_data VARCHAR(255),
    sheet_music TEXT,
    key_signature VARCHAR(50),
    chord_progression VARCHAR(100),
    scale VARCHAR(50),
    FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
);

-- Audio Fingerprints Table: Unique identification hashes
CREATE TABLE audio_fingerprints (
    fingerprint_id INT PRIMARY KEY,
    song_id INT UNIQUE NOT NULL,
    fingerprint_hash CHAR(64),
    algorithm VARCHAR(100),
    created_at DATETIME,
    FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
);

-- Lyric Translations Table: Non-primary language content
CREATE TABLE lyric_translations (
    translation_id INT PRIMARY KEY,
    song_id INT NOT NULL,
    target_language VARCHAR(50),
    translated_text TEXT,
    translator_agent VARCHAR(100),
    date_created DATETIME,
    FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
);

-- User Requests Table: Log of user interactions
CREATE TABLE user_requests (
    request_id INT PRIMARY KEY,
    user_input TEXT,
    detected_intent VARCHAR(255),
    agent_used VARCHAR(100),
    song_id INT NOT NULL,
    response_summary TEXT,
    timestamp DATETIME,
    FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
);

-- Recommendations Log Table: Records of songs recommended
CREATE TABLE recommendations_log (
    rec_id INT PRIMARY KEY,
    user_id VARCHAR(50),
    song_id INT NOT NULL,
    reason VARCHAR(255),
    confidence_score FLOAT(4, 3),
    timestamp DATETIME,
    FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
);

-- -----------------------------------------------------------------------------------
-- 2. Data Insertion (DML)
-- -----------------------------------------------------------------------------------

-- Insert into artists
INSERT INTO artists (artist_id, name, nationality, birth_year, description, spotify_id, youtube_channel) VALUES
(1, 'Fairuz', 'Lebanese', 1935, 'The legendary singer, known as "The jewel of Lebanon" and an icon of classical Arabic music (Tarab).', 'd27a17724a2c4e979ffcf1a1c3', 'Fairuz'),
(2, 'Nancy Ajram', 'Lebanese', 1983, 'A modern Arab pop superstar known for her catchy tunes and high production music videos.', '7c320d368e714a51b54a20b0b8', 'NancyAjram'),
(3, 'Mashrou\' Leila', 'Lebanese', 2008, 'An alternative rock band known for their progressive sound and often controversial, socially charged lyrics.', '20539169605d4b4fb24e4d580f', 'MashrouLeila'),
(4, 'Wael Kfoury', 'Lebanese', 1974, 'A star of romantic Arabic pop music, famous for his powerful voice and sentimental ballads.', 'b1491763e0044d038f4d2215f7', 'WaelKfoury'),
(5, 'Elissa', 'Lebanese', 1972, 'Known as the "Queen of Romance," specializing in highly emotional Arabic pop ballads.', '58c5a242c7af4711818a7c2c9d', 'Elissa'),
(6, 'Ragheb Alama', 'Lebanese', 1962, 'One of the best-selling Arab artists, often associated with upbeat, driving pop and dance tracks.', '9e8027732d844c80b5711b7593', 'RaghebAlama'),
(7, 'Assi El Hallani', 'Lebanese', 1970, 'Known for folk-pop music that often incorporates traditional Dabke rhythms.', 'a7ef1d8977c844979e2c6af942', 'AssiElHallani'),
(8, 'Ziad Rahbani', 'Lebanese', 1956, 'Composer, playwright, and satirist, known for his politically charged and jazz-influenced experimental music.', '2f3e82b7b55f4639918a5e1d53', 'ZiadRahbani'),
(9, 'Majida El Roumi', 'Lebanese', 1956, 'A renowned Arabic soprano, famed for her powerful voice and epic, orchestral ballads.', 'e182372545d9472fb8b21c430e', 'MajidaElRoumi'),
(10, 'Marcel Khalife', 'Lebanese', 1950, 'Master oud player and composer known for setting Mahmoud Darwish\'s poetry to music.', '35309d43553240e488d5573420', 'MarcelKhalife');

-- Insert into albums
INSERT INTO albums (album_id, title, artist_id, release_year, cover_url) VALUES
(101, 'Early Recordings (Compilation)', 1, 1967, 'http://img.example.com/album_101.jpg'),
(102, 'Ya Tabtab...', 2, 2006, 'http://img.example.com/album_102.jpg'),
(103, 'Raasuk', 3, 2011, 'http://img.example.com/album_103.jpg'),
(104, 'Kfoury 2007', 4, 2007, 'http://img.example.com/album_104.jpg'),
(105, 'Ayami Bik', 5, 2008, 'http://img.example.com/album_105.jpg'),
(106, 'Yalla', 6, 2010, 'http://img.example.com/album_106.jpg'),
(107, 'Ya Naker El Ma''rouf', 7, 2000, 'http://img.example.com/album_107.jpg'),
(108, 'Bema Enno', 8, 1996, 'http://img.example.com/album_108.jpg'),
(109, 'Oudou Ya Zaman', 9, 1982, 'http://img.example.com/album_109.jpg'),
(110, 'Passport', 10, 1990, 'http://img.example.com/album_110.jpg');
INSERT INTO songs (song_id, title, artist_id, album_id, release_year, genre, bpm, key_signature, duration_seconds, mood, language, spotify_id, youtube_id, audio_url) VALUES
-- Fairuz (Artist 1, Album 101) - Classical Tarab
(1001, 'Zahrat El Mada''en', 1, 101, 1967, 'Classical Arabic/Tarab', 81, 'F# Minor', 354, 'Somber/Patriotic', 'Arabic (Levantine)', '6a27e948c27943f2908f5127d4', 'd9479b19e92', 'http://media.example.com/audio/s1001.ogg'),
(1002, 'Bint El Shalabiya', 1, 101, 1952, 'Arabic Folk/Dabke', 135, 'D Major', 178, 'Happy/Traditional', 'Arabic (Levantine)', '5a1b5c468e82487e9545c85b88', '4b325257008', 'http://media.example.com/audio/s1002.ogg'),
(1003, 'Aatini Al Nay', 1, 101, 1961, 'Classical Arabic/Poetry', 64, 'C Minor', 290, 'Melancholy/Reflective', 'Arabic (Levantine)', '6849938830fe41718ec490c0a9', '38289417c8a', 'http://media.example.com/audio/s1003.ogg'),
(1004, 'Nassam Alayna El Hawa', 1, 101, 1970, 'Waltz/Tarab', 118, 'G Major', 255, 'Romantic/Nostalgic', 'Arabic (Levantine)', '521943c2c7d949cf9d2466ef4b', '5c4f275e7a9', 'http://media.example.com/audio/s1004.ogg'),

-- Nancy Ajram (Artist 2, Album 102) - Modern Pop
(1005, 'Ya Tabtab Wa Dalaa', 2, 102, 2006, 'Arabic Pop/Dance', 112, 'C Major', 260, 'Happy/Flirty', 'Arabic (Egyptian)', 'b9c71a39f67a42ec86a34795e1', 'a191f6804a7', 'http://media.example.com/audio/s1005.ogg'),
(1006, 'Ah W Noss', 2, 102, 2004, 'Pop Dance', 125, 'Bb Major', 242, 'Vibrant/Confident', 'Arabic (Egyptian)', 'a5c2ec4ecb1a43a0ae5021c35c', '4b74e1d3e11', 'http://media.example.com/audio/s1006.ogg'),
(1007, 'Inta Eyh', 2, 102, 2004, 'Pop Ballad', 95, 'A Minor', 270, 'Emotional/Dramatic', 'Arabic (Egyptian)', '63c5d63f90b943d6a1b24e4c27', 'a8c1f930e19', 'http://media.example.com/audio/s1007.ogg'),
(1008, 'Ehsas Gedeed', 2, 102, 2006, 'Pop Ballad', 105, 'Eb Major', 250, 'Romantic/Uplifting', 'Arabic (Egyptian)', '079979b0c7444c5f9426f8373b', '6715f57e84f', 'http://media.example.com/audio/s1008.ogg'),

-- Mashrou' Leila (Artist 3, Album 103) - Alternative Rock
(1009, 'Raksit Leila', 3, 103, 2011, 'Indie Rock/Alternative', 128, 'D Minor', 288, 'Intense/Rebellious', 'Arabic (Levantine)', '375276e0ef0042f0b484501a37', 'a33b08e5c3e', 'http://media.example.com/audio/s1009.ogg'),
(1010, 'Inni Mneeh', 3, 103, 2011, 'Post-Punk', 145, 'E Minor', 225, 'Anxious/Driving', 'Arabic (Levantine)', '831d102e35324e9fb2212f1737', 'c8173fa7329', 'http://media.example.com/audio/s1010.ogg'),
(1011, 'Cavalry', 3, 103, 2011, 'Alternative Ballad', 98, 'G Minor', 315, 'Calm/Sorrowful', 'Arabic (Levantine)', '915f07a72384414e8832a832c6', '9403d7c5770', 'http://media.example.com/audio/s1011.ogg'),
(1012, 'Fasateen', 3, 103, 2011, 'Art Rock', 123, 'B Minor', 241, 'Witty/Cynical', 'Arabic (Levantine)', '1259c4b786194b6697a21356f9', '14f32ed244e', 'http://media.example.com/audio/s1012.ogg'),

-- Wael Kfoury (Artist 4, Album 104) - Romantic Pop
(1013, 'Ma Fi Law', 4, 104, 2007, 'Romantic Pop', 98, 'A Major', 250, 'Romantic/Longing', 'Arabic (Levantine)', '662b6671049942a492193b219e', 'f4e1f74f762', 'http://media.example.com/audio/s1013.ogg'),
(1014, 'Mish Darour', 4, 104, 2007, 'Pop Ballad', 85, 'C# Minor', 268, 'Sorrowful/Heartbreak', 'Arabic (Levantine)', '38fa220b33a74656911762c2f7', '585093138b3', 'http://media.example.com/audio/s1014.ogg'),
(1015, 'Sirt We Sarit', 4, 104, 2007, 'Mid-Tempo Pop', 111, 'E Major', 234, 'Vibrant/Driving', 'Arabic (Levantine)', 'd1f4ce62089748b9816f1a8c3e', 'b2b804c7d6c', 'http://media.example.com/audio/s1015.ogg'),
(1016, 'Hakam Al Alb', 4, 104, 2007, 'Pop Ballad', 101, 'A Major', 288, 'Romantic/Longing', 'Arabic (Levantine)', 'df45d9b5006b432a9c37920154', 'a98f1338d81', 'http://media.example.com/audio/s1016.ogg'),

-- Elissa (Artist 5, Album 105) - Emotional Ballads
(1017, 'Betmoun', 5, 105, 2008, 'Arabic Ballad', 75, 'G Minor', 310, 'Emotional/Mellow', 'Arabic (Egyptian)', 'e7c629553535492d9d9f9cc10a', 'a937a075e7a', 'http://media.example.com/audio/s1017.ogg'),
(1018, 'Awakher El Shita', 5, 105, 2008, 'Pop Ballad', 65, 'F Major', 346, 'Reflective/Neutral', 'Arabic (Egyptian)', '63c5011933e4492383c2670d99', 'a4410a88b13', 'http://media.example.com/audio/s1018.ogg'),
(1019, 'Kermalak', 5, 105, 2008, 'Orchestral Pop', 84, 'Bb Major', 294, 'Emotional/Mellow', 'Arabic (Egyptian)', '67b36f7ce9324c47b5947a110a', '224e03d408f', 'http://media.example.com/audio/s1019.ogg'),
(1020, 'Ayami Bik', 5, 105, 2008, 'Mellow Pop', 88, 'G Minor', 349, 'Emotional/Mellow', 'Arabic (Egyptian)', '684992485e7e4860b21a37803e', '12f205a1099', 'http://media.example.com/audio/s1020.ogg'),

-- Ragheb Alama (Artist 6, Album 106) - Upbeat Pop/Dance
(1021, 'Albi Asheqha', 6, 106, 2010, 'Upbeat Pop/Dance', 125, 'E Minor', 220, 'Celebratory/Driving', 'Arabic (Levantine)', 'f2053075c2e148e69212040e69', '32a52d7c5ed', 'http://media.example.com/audio/s1021.ogg'),
(1022, 'Saharouny El Layl', 6, 106, 2001, 'Eurodance/Pop', 135, 'C Major', 241, 'Celebratory/Driving', 'Arabic (Levantine)', '99026365a6e846059d08e5e1e1', 'a191f6804a7', 'http://media.example.com/audio/s1022.ogg'),
(1023, 'Yalla', 6, 106, 2010, 'Summer Hit/Pop', 128, 'A Major', 253, 'Upbeat/Positive', 'Arabic (Levantine)', 'b9c71a39f67a42ec86a34795e1', '4b74e1d3e11', 'http://media.example.com/audio/s1023.ogg'),
(1024, 'Nessini El Donya', 6, 106, 2008, 'Pop Funk', 122, 'F Minor', 215, 'Romantic/Funky', 'Arabic (Levantine)', '6a27e948c27943f2908f5127d4', 'a8c1f930e19', 'http://media.example.com/audio/s1024.ogg'),

-- Assi El Hallani (Artist 7, Album 107) - Folk Pop/Dabke
(1025, 'Ya Tayr', 7, 107, 2000, 'Folk Pop/Dabke', 140, 'B Major', 245, 'Traditional/Energetic', 'Arabic (Levantine)', '5a1b5c468e82487e9545c85b88', '6715f57e84f', 'http://media.example.com/audio/s1025.ogg'),
(1026, 'Wani Mareg Marrait', 7, 107, 2000, 'Folk Dance/Dabke', 158, 'D Minor', 205, 'Traditional/Energetic', 'Arabic (Levantine)', '6849938830fe41718ec490c0a9', 'c8173fa7329', 'http://media.example.com/audio/s1026.ogg'),
(1027, 'Hawa Beirut', 7, 107, 2000, 'Traditional Instrumental', 115, 'A Major', 204, 'Vibrant/Nostalgic', 'Arabic (Levantine)', '521943c2c7d949cf9d2466ef4b', '9403d7c5770', 'http://media.example.com/audio/s1027.ogg'),
(1028, 'Ya Naker El Ma''rouf', 7, 107, 2000, 'World Fusion/Folk', 130, 'B Minor', 203, 'Melancholy/Energetic', 'Arabic (Levantine)', 'b9c71a39f67a42ec86a34795e1', '14f32ed244e', 'http://media.example.com/audio/s1028.ogg'),

-- Ziad Rahbani (Artist 8, Album 108) - Jazz/Experimental
(1029, 'Bema Enno', 8, 108, 1996, 'Jazz/Experimental', 105, 'Bb Major', 420, 'Witty/Cynical', 'Arabic (Levantine)', '20539169605d4b4fb24e4d580f', 'f4e1f74f762', 'http://media.example.com/audio/s1029.ogg'),
(1030, 'Shi Fashil', 8, 108, 1996, 'Bossa Nova/Spoken Word', 93, 'G Major', 393, 'Neutral/Sarcastic', 'Arabic (Levantine)', 'b1491763e0044d038f4d2215f7', '585093138b3', 'http://media.example.com/audio/s1030.ogg'),
(1031, 'Marjouha', 8, 108, 1996, 'Instrumental Jam/Jazz Fusion', 113, 'C Minor', 397, 'Calm/Atmospheric', 'Arabic (Levantine)', '58c5a242c7af4711818a7c2c9d', 'b2b804c7d6c', 'http://media.example.com/audio/s1031.ogg'),
(1032, 'Ismaa Ya Rida', 8, 108, 1996, 'Fusion Jazz/Satirical', 96, 'D Minor', 450, 'Witty/Cynical', 'Arabic (Levantine)', '9e8027732d844c80b5711b7593', 'a98f1338d81', 'http://media.example.com/audio/s1032.ogg'),

-- Majida El Roumi (Artist 9, Album 109) - Orchestral Tarab
(1033, 'Mutafarriqah', 9, 109, 1982, 'Tarab/Orchestral', 68, 'C Minor', 380, 'Epic/Dramatic', 'Arabic (Classical)', 'a7ef1d8977c844979e2c6af942', 'a937a075e7a', 'http://media.example.com/audio/s1033.ogg'),
(1034, 'E''tizali', 9, 109, 1982, 'Dramatic Ballad', 78, 'F# Minor', 342, 'Epic/Dramatic', 'Arabic (Classical)', '2f3e82b7b55f4639918a5e1d53', 'a4410a88b13', 'http://media.example.com/audio/s1034.ogg'),
(1035, 'Sayf Ya Koun', 9, 109, 1982, 'Symphonic/Ballad', 57, 'Eb Major', 400, 'Epic/Dramatic', 'Arabic (Classical)', 'e182372545d9472fb8b21c430e', '224e03d408f', 'http://media.example.com/audio/s1035.ogg'),
(1036, 'Oudou Ya Zaman', 9, 109, 1982, 'Film Score/Ballad', 83, 'A Minor', 365, 'Neutral/Reflective', 'Arabic (Classical)', '35309d43553240e488d5573420', '12f205a1099', 'http://media.example.com/audio/s1036.ogg'),

-- Marcel Khalife (Artist 10, Album 110) - Folk/Oud/Political
(1037, 'Passport', 10, 110, 1990, 'Folk/Oud/Political', 90, 'A Minor', 330, 'Political/Acoustic', 'Arabic (Classical/Poetry)', '6a27e948c27943f2908f5127d4', '32a52d7c5ed', 'http://media.example.com/audio/s1037.ogg'),
(1038, 'Rita Wal Bunduqiya', 10, 110, 1980, 'Poetry Recital/Oud', 82, 'C Minor', 347, 'Political/Acoustic', 'Arabic (Classical/Poetry)', '5a1b5c468e82487e9545c85b88', 'a191f6804a7', 'http://media.example.com/audio/s1038.ogg'),
(1039, 'Jameel Al Marahil', 10, 110, 1990, 'Instrumental Medley/Oud', 105, 'G Minor', 308, 'Calm/Instrumental', 'Arabic (Classical/Poetry)', '6849938830fe41718ec490c0a9', '4b74e1d3e11', 'http://media.example.com/audio/s1039.ogg'),
(1040, 'Ahla Fi Houkoumat El Banadoura', 10, 110, 2023, 'Acoustic Folk/Satirical', 91, 'D Major', 315, 'Political/Acoustic', 'Arabic (Classical/Poetry)', '521943c2c7d949cf9d2466ef4b', 'a8c1f930e19', 'http://media.example.com/audio/s1040.ogg');


-- Insert into lyrics
INSERT INTO lyrics (lyric_id, song_id, lyric_text, language, source) VALUES
(2001, 1001, 'Zahrat El Mada''en\nYā zahrat al-madāʼin, yā quds\nYā madīnat al-lawz al-murr\nWa lā sharaf li-al-radd', 'Arabic (Levantine)', 'Manual Entry/Derived Data'),
(2002, 1002, 'Derived lyrics for Fairuz in the style of Waltz.', 'Arabic (Levantine)', 'Manual Entry/Derived Data'),
(2003, 1003, 'Derived lyrics for Fairuz in the style of Classical Instrumental.', 'Arabic (Levantine)', 'Manual Entry/Derived Data'),
(2004, 1004, 'Derived lyrics for Fairuz in the style of Tarab.', 'Arabic (Levantine)', 'Manual Entry/Derived Data'),
(2005, 1005, 'Yā ṭabṭab wā dallā''\nWā yā lulū'' wā yā ānā\nLaw yishūfu ḥubbak ḥadd', 'Arabic (Egyptian)', 'Manual Entry/Derived Data'),
(2006, 1006, 'Derived lyrics for Nancy Ajram in the style of Club Pop.', 'Arabic (Egyptian)', 'Manual Entry/Derived Data'),
(2007, 1007, 'Derived lyrics for Nancy Ajram in the style of Pop Dance.', 'Arabic (Egyptian)', 'Manual Entry/Derived Data'),
(2008, 1008, 'Derived lyrics for Nancy Ajram in the style of Electronic Remix.', 'Arabic (Egyptian)', 'Manual Entry/Derived Data'),
(2009, 1009, 'Wā qālū, qālū\nAl-qalb mā bi-yiḥmil\nAl-ḥubbu mā bi-yiṣmad', 'Arabic (Levantine)', 'Manual Entry/Derived Data'),
(2010, 1010, 'Derived lyrics for Mashrou'' Leila in the style of Punk Revival.', 'Arabic (Levantine)', 'Manual Entry/Derived Data'),
(2011, 1011, 'Derived lyrics for Mashrou'' Leila in the style of Alternative Ballad.', 'Arabic (Levantine)', 'Manual Entry/Derived Data'),
(2012, 1012, 'Derived lyrics for Mashrou'' Leila in the style of Art Rock.', 'Arabic (Levantine)', 'Manual Entry/Derived Data'),
(2013, 1013, 'Ma fi law, wala kayf\nInta albi, inta nuri\nYa habibi, ya ghali', 'Arabic (Levantine)', 'Manual Entry/Derived Data'),
(2014, 1014, 'Derived lyrics for Wael Kfoury in the style of Acoustic Cover.', 'Arabic (Levantine)', 'Manual Entry/Derived Data'),
(2015, 1015, 'Derived lyrics for Wael Kfoury in the style of Mid-Tempo Pop.', 'Arabic (Levantine)', 'Manual Entry/Derived Data'),
(2016, 1016, 'Derived lyrics for Wael Kfoury in the style of Pop Ballad.', 'Arabic (Levantine)', 'Manual Entry/Derived Data'),
(2017, 1017, 'Bitmūn, bitmūn, ya ḥabibi\nAlbi bi-ḥibbak, ya ḥayati\nMā ba''dar ‘ala nisyānak', 'Arabic (Egyptian)', 'Manual Entry/Derived Data'),
(2018, 1018, 'Derived lyrics for Elissa in the style of Acoustic Ballad.', 'Arabic (Egyptian)', 'Manual Entry/Derived Data'),
(2019, 1019, 'Derived lyrics for Elissa in the style of Orchestral Pop.', 'Arabic (Egyptian)', 'Manual Entry/Derived Data'),
(2020, 1020, 'Derived lyrics for Elissa in the style of Mellow Pop.', 'Arabic (Egyptian)', 'Manual Entry/Derived Data'),
(2021, 1021, 'Albi ''āshiqhā, w-rūḥi ma''āha\nYa ''ayni, ya layl\nYallā ya ḥabibi', 'Arabic (Levantine)', 'Manual Entry/Derived Data'),
(2022, 1022, 'Derived lyrics for Ragheb Alama in the style of Eurodance.', 'Arabic (Levantine)', 'Manual Entry/Derived Data'),
(2023, 1023, 'Derived lyrics for Ragheb Alama in the style of Summer Hit.', 'Arabic (Levantine)', 'Manual Entry/Derived Data'),
(2024, 1024, 'Derived lyrics for Ragheb Alama in the style of Pop Funk.', 'Arabic (Levantine)', 'Manual Entry/Derived Data'),
(2025, 1025, 'Yā ṭayr il-ghābi\nSaflak, salli''l-qalb\nWi-rja'' lī ḥabibi', 'Arabic (Levantine)', 'Manual Entry/Derived Data'),
(2026, 1026, 'Derived lyrics for Assi El Hallani in the style of Folk Dance.', 'Arabic (Levantine)', 'Manual Entry/Derived Data'),
(2027, 1027, 'Derived lyrics for Assi El Hallani in the style of Traditional Instrumental.', 'Arabic (Levantine)', 'Manual Entry/Derived Data'),
(2028, 1028, 'Derived lyrics for Assi El Hallani in the style of World Fusion.', 'Arabic (Levantine)', 'Manual Entry/Derived Data'),
(2029, 1029, 'Bi-mā innū ma fīh amal\nYa''nī shū bidna na''mil\nKhallīna n-ḍaḥak', 'Arabic (Levantine)', 'Manual Entry/Derived Data'),
(2030, 1030, 'Derived lyrics for Ziad Rahbani in the style of Bossa Nova.', 'Arabic (Levantine)', 'Manual Entry/Derived Data'),
(2031, 1031, 'Derived lyrics for Ziad Rahbani in the style of Instrumental Jam.', 'Arabic (Levantine)', 'Manual Entry/Derived Data'),
(2032, 1032, 'Derived lyrics for Ziad Rahbani in the style of Fusion Jazz.', 'Arabic (Levantine)', 'Manual Entry/Derived Data'),
(2033, 1033, 'Mutafarriqah, fi riḥlat il-nujūm\nWa kullu shāy'' yumkin an yaḥduth\nFi hadhih il-dunyā', 'Arabic (Classical)', 'Manual Entry/Derived Data'),
(2034, 1034, 'Derived lyrics for Majida El Roumi in the style of Dramatic Ballad.', 'Arabic (Classical)', 'Manual Entry/Derived Data'),
(2035, 1035, 'Derived lyrics for Majida El Roumi in the style of Symphonic.', 'Arabic (Classical)', 'Manual Entry/Derived Data'),
(2036, 1036, 'Derived lyrics for Majida El Roumi in the style of Film Score.', 'Arabic (Classical)', 'Manual Entry/Derived Data'),
(2037, 1037, 'Li-mādhā n-kūn al-mū''allamūn\nLi-mādhā n-kūn al-ghurabā''\nFil-waṭan al-kabīr', 'Arabic (Classical/Poetry)', 'Manual Entry/Derived Data'),
(2038, 1038, 'Derived lyrics for Marcel Khalife in the style of Poetry Recital.', 'Arabic (Classical/Poetry)', 'Manual Entry/Derived Data'),
(2039, 1039, 'Derived lyrics for Marcel Khalife in the style of Instrumental Medley.', 'Arabic (Classical/Poetry)', 'Manual Entry/Derived Data'),
(2040, 1040, 'Derived lyrics for Marcel Khalife in the style of Acoustic Folk.', 'Arabic (Classical/Poetry)', 'Manual Entry/Derived Data');

-- Insert into song_features
INSERT INTO song_features (feature_id, song_id, danceability, energy, valence, acousticness, instrumentalness, liveness, speechiness, mode, loudness) VALUES
(3001, 1001, 0.250, 0.300, 0.150, 0.950, 0.700, 0.150, 0.050, 0, -15.00),
(3002, 1002, 0.198, 0.165, 0.233, 0.990, 0.612, 0.059, 0.057, 0, -16.59),
(3003, 1003, 0.156, 0.279, 0.118, 0.825, 0.816, 0.129, 0.043, 0, -17.29),
(3004, 1004, 0.176, 0.244, 0.119, 0.817, 0.654, 0.080, 0.038, 0, -17.91),
(3005, 1005, 0.850, 0.750, 0.920, 0.050, 0.001, 0.200, 0.100, 1, -5.50),
(3006, 1006, 0.958, 0.900, 0.945, 0.012, 0.000, 0.141, 0.111, 1, -2.57),
(3007, 1007, 0.937, 0.871, 0.985, 0.021, 0.000, 0.128, 0.081, 1, -1.97),
(3008, 1008, 0.803, 0.815, 0.781, 0.044, 0.000, 0.122, 0.062, 1, -0.66),
(3009, 1009, 0.550, 0.850, 0.400, 0.100, 0.005, 0.350, 0.080, 0, -6.80),
(3010, 1010, 0.449, 0.767, 0.509, 0.157, 0.000, 0.251, 0.091, 0, -2.97),
(3011, 1011, 0.617, 0.573, 0.301, 0.158, 0.003, 0.246, 0.063, 0, -9.14),
(3012, 1012, 0.672, 0.865, 0.489, 0.054, 0.002, 0.485, 0.056, 0, -4.84),
(3013, 1013, 0.650, 0.550, 0.680, 0.200, 0.000, 0.100, 0.030, 1, -7.50),
(3014, 1014, 0.546, 0.320, 0.578, 0.463, 0.000, 0.054, 0.019, 1, -10.42),
(3015, 1015, 0.722, 0.544, 0.784, 0.165, 0.000, 0.087, 0.029, 1, -5.99),
(3016, 1016, 0.785, 0.437, 0.547, 0.339, 0.000, 0.076, 0.029, 1, -10.16),
(3017, 1017, 0.400, 0.350, 0.250, 0.500, 0.010, 0.120, 0.040, 0, -10.50),
(3018, 1018, 0.368, 0.161, 0.260, 0.750, 0.000, 0.063, 0.023, 0, -14.04),
(3019, 1019, 0.486, 0.370, 0.395, 0.563, 0.024, 0.187, 0.053, 0, -8.32),
(3020, 1020, 0.439, 0.297, 0.170, 0.707, 0.006, 0.098, 0.044, 0, -13.29),
(3021, 1021, 0.880, 0.800, 0.950, 0.010, 0.000, 0.250, 0.080, 1, -4.50),
(3022, 1022, 0.941, 0.887, 0.990, 0.000, 0.000, 0.301, 0.076, 1, -0.99),
(3023, 1023, 0.932, 0.781, 0.814, 0.000, 0.000, 0.158, 0.093, 1, -2.18),
(3024, 1024, 0.793, 0.881, 0.996, 0.006, 0.000, 0.175, 0.067, 1, -2.12),
(3025, 1025, 0.780, 0.900, 0.850, 0.150, 0.000, 0.300, 0.120, 1, -6.00),
(3026, 1026, 0.889, 0.813, 0.870, 0.106, 0.000, 0.229, 0.134, 1, -2.48),
(3027, 1027, 0.771, 0.807, 0.985, 0.057, 0.000, 0.245, 0.102, 1, -4.68),
(3028, 1028, 0.835, 0.990, 0.966, 0.105, 0.000, 0.428, 0.117, 1, -2.44),
(3029, 1029, 0.500, 0.450, 0.550, 0.700, 0.300, 0.180, 0.070, 1, -12.00),
(3030, 1030, 0.589, 0.316, 0.528, 0.790, 0.288, 0.098, 0.060, 1, -14.65),
(3031, 1031, 0.490, 0.399, 0.655, 0.741, 0.435, 0.282, 0.055, 1, -12.28),
(3032, 1032, 0.518, 0.494, 0.449, 0.672, 0.203, 0.242, 0.060, 1, -10.37),
(3033, 1033, 0.200, 0.280, 0.100, 0.900, 0.550, 0.100, 0.030, 0, -16.50),
(3034, 1034, 0.283, 0.147, 0.054, 0.990, 0.550, 0.088, 0.022, 0, -19.00),
(3035, 1035, 0.143, 0.250, 0.021, 0.990, 0.650, 0.149, 0.033, 0, -18.78),
(3036, 1036, 0.208, 0.252, 0.165, 0.802, 0.479, 0.088, 0.028, 0, -19.00),
(3037, 1037, 0.350, 0.400, 0.200, 0.850, 0.600, 0.150, 0.060, 0, -13.00),
(3038, 1038, 0.404, 0.206, 0.298, 0.990, 0.569, 0.092, 0.043, 0, -15.93),
(3039, 1039, 0.405, 0.301, 0.117, 0.990, 0.750, 0.187, 0.045, 0, -15.42),
(3040, 1040, 0.316, 0.540, 0.208, 0.812, 0.536, 0.252, 0.057, 0, -11.02);

-- Insert into lyric_translations (Only for Arabic songs)
INSERT INTO lyric_translations (translation_id, song_id, target_language, translated_text, translator_agent, date_created) VALUES
(4001, 1001, 'English', '[English translation for Zahrat El Mada''en]. Focused on the theme of somber/patriotic.', 'LLM_Translator_V2', '2025-11-16T22:49:18.067341'),
(4002, 1002, 'English', '[English translation for Fairuz - Derived Track 1 (Waltz)]. Focused on the theme of calm.', 'LLM_Translator_V2', '2025-10-31T22:49:18.067425'),
(4003, 1003, 'English', '[English translation for Fairuz - Derived Track 2 (Classical Instrumental)]. Focused on the theme of calm.', 'LLM_Translator_V2', '2025-11-09T22:49:18.067448'),
(4004, 1004, 'English', '[English translation for Fairuz - Derived Track 3 (Tarab)]. Focused on the theme of neutral.', 'LLM_Translator_V2', '2025-11-13T22:49:18.067468'),
(4005, 1005, 'English', '[English translation for Ya Tabtab Wa Dalaa]. Focused on the theme of happy/flirty.', 'LLM_Translator_V2', '2025-11-14T22:49:18.067487'),
(4006, 1006, 'English', '[English translation for Nancy Ajram - Derived Track 1 (Club Pop)]. Focused on the theme of vibrant.', 'LLM_Translator_V2', '2025-11-04T22:49:18.067507'),
(4007, 1007, 'English', '[English translation for Nancy Ajram - Derived Track 2 (Pop Dance)]. Focused on the theme of vibrant.', 'LLM_Translator_V2', '2025-11-08T22:49:18.067530'),
(4008, 1008, 'English', '[English translation for Nancy Ajram - Derived Track 3 (Electronic Remix)]. Focused on the theme of happy/flirty.', 'LLM_Translator_V2', '2025-11-02T22:49:18.067550'),
(4009, 1009, 'English', '[English translation for Raksit Leila]. Focused on the theme of intense/rebellious.', 'LLM_Translator_V2', '2025-11-03T22:49:18.067570'),
(4010, 1010, 'English', '[English translation for Mashrou'' Leila - Derived Track 1 (Punk Revival)]. Focused on the theme of intense/rebellious.', 'LLM_Translator_V2', '2025-10-24T22:49:18.067590'),
(4011, 1011, 'English', '[English translation for Mashrou'' Leila - Derived Track 2 (Alternative Ballad)]. Focused on the theme of calm.', 'LLM_Translator_V2', '2025-11-07T22:49:18.067609'),
(4012, 1012, 'English', '[English translation for Mashrou'' Leila - Derived Track 3 (Art Rock)]. Focused on the theme of intense/rebellious.', 'LLM_Translator_V2', '2025-11-13T22:49:18.067628'),
(4013, 1013, 'English', '[English translation for Ma Fi Law]. Focused on the theme of romantic/longing.', 'LLM_Translator_V2', '2025-10-28T22:49:18.067647'),
(4014, 1014, 'English', '[English translation for Wael Kfoury - Derived Track 1 (Acoustic Cover)]. Focused on the theme of romantic/longing.', 'LLM_Translator_V2', '2025-11-08T22:49:18.067666'),
(4015, 1015, 'English', '[English translation for Wael Kfoury - Derived Track 2 (Mid-Tempo Pop)]. Focused on the theme of vibrant.', 'LLM_Translator_V2', '2025-11-08T22:49:18.067684'),
(4016, 1016, 'English', '[English translation for Wael Kfoury - Derived Track 3 (Pop Ballad)]. Focused on the theme of romantic/longing.', 'LLM_Translator_V2', '2025-11-12T22:49:18.067702'),
(4017, 1017, 'English', '[English translation for Betmoun]. Focused on the theme of emotional/mellow.', 'LLM_Translator_V2', '2025-11-09T22:49:18.067720'),
(4018, 1018, 'English', '[English translation for Elissa - Derived Track 1 (Acoustic Ballad)]. Focused on the theme of neutral.', 'LLM_Translator_V2', '2025-10-31T22:49:18.067737'),
(4019, 1019, 'English', '[English translation for Elissa - Derived Track 2 (Orchestral Pop)]. Focused on the theme of emotional/mellow.', 'LLM_Translator_V2', '2025-11-02T22:49:18.067755'),
(4020, 1020, 'English', '[English translation for Elissa - Derived Track 3 (Mellow Pop)]. Focused on the theme of emotional/mellow.', 'LLM_Translator_V2', '2025-11-10T22:49:18.067773'),
(4021, 1021, 'English', '[English translation for Albi Asheqha]. Focused on the theme of celebratory/driving.', 'LLM_Translator_V2', '2025-11-03T22:49:18.067790'),
(4022, 1022, 'English', '[English translation for Ragheb Alama - Derived Track 1 (Eurodance)]. Focused on the theme of celebratory/driving.', 'LLM_Translator_V2', '2025-11-10T22:49:18.067807'),
(4023, 1023, 'English', '[English translation for Ragheb Alama - Derived Track 2 (Summer Hit)]. Focused on the theme of neutral.', 'LLM_Translator_V2', '2025-11-07T22:49:18.067824'),
(4024, 1024, 'English', '[English translation for Ragheb Alama - Derived Track 3 (Pop Funk)]. Focused on the theme of celebratory/driving.', 'LLM_Translator_V2', '2025-11-02T22:49:18.067841'),
(4025, 1025, 'English', '[English translation for Ya Tayr]. Focused on the theme of traditional/energetic.', 'LLM_Translator_V2', '2025-11-15T22:49:18.067859'),
(4026, 1026, 'English', '[English translation for Assi El Hallani - Derived Track 1 (Folk Dance)]. Focused on the theme of traditional/energetic.', 'LLM_Translator_V2', '2025-11-04T22:49:18.067876'),
(4027, 1027, 'English', '[English translation for Assi El Hallani - Derived Track 2 (Traditional Instrumental)]. Focused on the theme of vibrant.', 'LLM_Translator_V2', '2025-11-11T22:49:18.067894'),
(4028, 1028, 'English', '[English translation for Assi El Hallani - Derived Track 3 (World Fusion)]. Focused on the theme of traditional/energetic.', 'LLM_Translator_V2', '2025-11-05T22:49:18.067911'),
(4029, 1029, 'English', '[English translation for Bema Enno]. Focused on the theme of witty/cynical.', 'LLM_Translator_V2', '2025-11-06T22:49:18.067929'),
(4030, 1030, 'English', '[English translation for Ziad Rahbani - Derived Track 1 (Bossa Nova)]. Focused on the theme of neutral.', 'LLM_Translator_V2', '2025-11-04T22:49:18.067946'),
(4031, 1031, 'English', '[English translation for Ziad Rahbani - Derived Track 2 (Instrumental Jam)]. Focused on the theme of calm.', 'LLM_Translator_V2', '2025-11-08T22:49:18.067964'),
(4032, 1032, 'English', '[English translation for Ziad Rahbani - Derived Track 3 (Fusion Jazz)]. Focused on the theme of witty/cynical.', 'LLM_Translator_V2', '2025-11-01T22:49:18.067981'),
(4033, 1033, 'English', '[English translation for Mutafarriqah]. Focused on the theme of epic/dramatic.', 'LLM_Translator_V2', '2025-11-05T22:49:18.067998'),
(4034, 1034, 'English', '[English translation for Majida El Roumi - Derived Track 1 (Dramatic Ballad)]. Focused on the theme of epic/dramatic.', 'LLM_Translator_V2', '2025-11-13T22:49:18.068015'),
(4035, 1035, 'English', '[English translation for Majida El Roumi - Derived Track 2 (Symphonic)]. Focused on the theme of epic/dramatic.', 'LLM_Translator_V2', '2025-11-02T22:49:18.068032'),
(4036, 1036, 'English', '[English translation for Majida El Roumi - Derived Track 3 (Film Score)]. Focused on the theme of neutral.', 'LLM_Translator_V2', '2025-11-12T22:49:18.068049'),
(4037, 1037, 'English', '[English translation for Passport]. Focused on the theme of political/acoustic.', 'LLM_Translator_V2', '2025-11-13T22:49:18.068067'),
(4038, 1038, 'English', '[English translation for Marcel Khalife - Derived Track 1 (Poetry Recital)]. Focused on the theme of political/acoustic.', 'LLM_Translator_V2', '2025-10-27T22:49:18.068084'),
(4039, 1039, 'English', '[English translation for Marcel Khalife - Derived Track 2 (Instrumental Medley)]. Focused on the theme of calm.', 'LLM_Translator_V2', '2025-11-06T22:49:18.068102'),
(4040, 1040, 'English', '[English translation for Marcel Khalife - Derived Track 3 (Acoustic Folk)]. Focused on the theme of political/acoustic.', 'LLM_Translator_V2', '2025-11-14T22:49:18.068119');

-- Insert into music_notes
INSERT INTO music_notes (note_id, song_id, midi_data, sheet_music, key_signature, chord_progression, scale) VALUES
(5001, 1001, '0xd3617300f862... (BLOB placeholder)', 'Key of F# Minor. Melody score available.', 'F# Minor', 'C-G-Am-F', 'Minor'),
(5002, 1002, '0x2213763f0340... (BLOB placeholder)', 'Key of F# Minor. Melody score available.', 'F# Minor', 'C-G-Am-F', 'Phrygian'),
(5003, 1003, '0x8f78a7f0e69e... (BLOB placeholder)', 'Key of F# Minor. Melody score available.', 'F# Minor', 'Dm-Am-C-G', 'Hijaz'),
(5004, 1004, '0x7b669e2c69d8... (BLOB placeholder)', 'Key of F# Minor. Melody score available.', 'F# Minor', 'Am-G-C-F', 'Major'),
(5005, 1005, '0x00f86235478d... (BLOB placeholder)', 'Key of C Major. Melody score available.', 'C Major', 'C-G-Am-F', 'Major'),
(5006, 1006, '0x217e812f8626... (BLOB placeholder)', 'Key of C Major. Melody score available.', 'C Major', 'Am-G-C-F', 'Major'),
(5007, 1007, '0xd641c88147d3... (BLOB placeholder)', 'Key of C Major. Melody score available.', 'C Major', 'Dm-Am-C-G', 'Minor'),
(5008, 1008, '0x5c72d627c24f... (BLOB placeholder)', 'Key of C Major. Melody score available.', 'C Major', 'Cm-Gm-Eb-Bb', 'Major'),
(5009, 1009, '0x321356e72b03... (BLOB placeholder)', 'Key of D Minor. Melody score available.', 'D Minor', 'Cm-Gm-Eb-Bb', 'Minor'),
(5010, 1010, '0x7e812f8626c9... (BLOB placeholder)', 'Key of D Minor. Melody score available.', 'D Minor', 'Dm-Am-C-G', 'Major'),
(5011, 1011, '0xd48731309d43... (BLOB placeholder)', 'Key of D Minor. Melody score available.', 'D Minor', 'C-G-Am-F', 'Minor'),
(5012, 1012, '0x70fa72718e24... (BLOB placeholder)', 'Key of D Minor. Melody score available.', 'D Minor', 'Am-G-C-F', 'Major'),
(5013, 1013, '0x210c326b4847... (BLOB placeholder)', 'Key of A Major. Melody score available.', 'A Major', 'C-G-Am-F', 'Major'),
(5014, 1014, '0x2d32a52d7c5e... (BLOB placeholder)', 'Key of A Major. Melody score available.', 'A Major', 'Dm-Am-C-G', 'Major'),
(5015, 1015, '0x33b08e5c3e7b... (BLOB placeholder)', 'Key of A Major. Melody score available.', 'A Major', 'Cm-Gm-Eb-Bb', 'Phrygian'),
(5016, 1016, '0xb563c7849938... (BLOB placeholder)', 'Key of A Major. Melody score available.', 'A Major', 'Am-G-C-F', 'Minor'),
(5017, 1017, '0xd3617300f862... (BLOB placeholder)', 'Key of G Minor. Melody score available.', 'G Minor', 'C-G-Am-F', 'Minor'),
(5018, 1018, '0x2213763f0340... (BLOB placeholder)', 'Key of G Minor. Melody score available.', 'G Minor', 'Cm-Gm-Eb-Bb', 'Minor'),
(5019, 1019, '0x8f78a7f0e69e... (BLOB placeholder)', 'Key of G Minor. Melody score available.', 'G Minor', 'Am-G-C-F', 'Minor'),
(5020, 1020, '0x7b669e2c69d8... (BLOB placeholder)', 'Key of G Minor. Melody score available.', 'G Minor', 'Dm-Am-C-G', 'Minor'),
(5021, 1021, '0x00f86235478d... (BLOB placeholder)', 'Key of E Minor. Melody score available.', 'E Minor', 'Am-G-C-F', 'Major'),
(5022, 1022, '0x217e812f8626... (BLOB placeholder)', 'Key of E Minor. Melody score available.', 'E Minor', 'Dm-Am-C-G', 'Major'),
(5023, 1023, '0xd641c88147d3... (BLOB placeholder)', 'Key of E Minor. Melody score available.', 'E Minor', 'Cm-Gm-Eb-Bb', 'Hijaz'),
(5024, 1024, '0x5c72d627c24f... (BLOB placeholder)', 'Key of E Minor. Melody score available.', 'E Minor', 'C-G-Am-F', 'Major'),
(5025, 1025, '0x321356e72b03... (BLOB placeholder)', 'Key of B Major. Melody score available.', 'B Major', 'C-G-Am-F', 'Major'),
(5026, 1026, '0x7e812f8626c9... (BLOB placeholder)', 'Key of B Major. Melody score available.', 'B Major', 'Am-G-C-F', 'Major'),
(5027, 1027, '0xd48731309d43... (BLOB placeholder)', 'Key of B Major. Melody score available.', 'B Major', 'Cm-Gm-Eb-Bb', 'Phrygian'),
(5028, 1028, '0x70fa72718e24... (BLOB placeholder)', 'Key of B Major. Melody score available.', 'B Major', 'Dm-Am-C-G', 'Major'),
(5029, 1029, '0x210c326b4847... (BLOB placeholder)', 'Key of Bb Major. Melody score available.', 'Bb Major', 'Am-G-C-F', 'Minor'),
(5030, 1030, '0x2d32a52d7c5e... (BLOB placeholder)', 'Key of Bb Major. Melody score available.', 'Bb Major', 'Dm-Am-C-G', 'Minor'),
(5031, 1031, '0x33b08e5c3e7b... (BLOB placeholder)', 'Key of Bb Major. Melody score available.', 'Bb Major', 'C-G-Am-F', 'Major'),
(5032, 1032, '0xb563c7849938... (BLOB placeholder)', 'Key of Bb Major. Melody score available.', 'Bb Major', 'Cm-Gm-Eb-Bb', 'Minor'),
(5033, 1033, '0xd3617300f862... (BLOB placeholder)', 'Key of C Minor. Melody score available.', 'C Minor', 'C-G-Am-F', 'Minor'),
(5034, 1034, '0x2213763f0340... (BLOB placeholder)', 'Key of C Minor. Melody score available.', 'C Minor', 'Dm-Am-C-G', 'Hijaz'),
(5035, 1035, '0x8f78a7f0e69e... (BLOB placeholder)', 'Key of C Minor. Melody score available.', 'C Minor', 'Am-G-C-F', 'Minor'),
(5036, 1036, '0x7b669e2c69d8... (BLOB placeholder)', 'Key of C Minor. Melody score available.', 'C Minor', 'Cm-Gm-Eb-Bb', 'Major'),
(5037, 1037, '0x00f86235478d... (BLOB placeholder)', 'Key of A Minor. Melody score available.', 'A Minor', 'C-G-Am-F', 'Phrygian'),
(5038, 1038, '0x217e812f8626... (BLOB placeholder)', 'Key of A Minor. Melody score available.', 'A Minor', 'Dm-Am-C-G', 'Minor'),
(5039, 1039, '0xd641c88147d3... (BLOB placeholder)', 'Key of A Minor. Melody score available.', 'A Minor', 'Am-G-C-F', 'Major'),
(5040, 1040, '0x5c72d627c24f... (BLOB placeholder)', 'Key of A Minor. Melody score available.', 'A Minor', 'Cm-Gm-Eb-Bb', 'Minor');

-- Insert into audio_fingerprints
INSERT INTO audio_fingerprints (fingerprint_id, song_id, fingerprint_hash, algorithm, created_at) VALUES
(6001, 1001, 'd9620a40f8074d06af461d9a2a9e59d997a3a307077e48b4887b64081c79e604', 'AcousticMatch_v3.1', '2025-11-12 22:49:18'),
(6002, 1002, '4d7a83d3600c436fb247d487210c326b48472f8626c997321356e72b03d641c8', 'AcousticMatch_v3.1', '2025-11-13 22:49:18'),
(6003, 1003, '7e812f8626c997321356e72b03d641c88147d3c01b9c71a39f67a42ec86a34795', 'AcousticMatch_v3.1', '2025-11-06 22:49:18'),
(6004, 1004, '3b593630f6584210a48d8b563c7849938830fe41718ec490c0a91e4f48483c74', 'AcousticMatch_v3.1', '2025-11-10 22:49:18'),
(6005, 1005, '12f205a109964580b080cc9074092497645d9b5006b432a9c37920154e17e812', 'AcousticMatch_v3.1', '2025-11-02 22:49:18'),
(6006, 1006, 'f4e1f74f762f4b74e1d3e11079979b0c7444c5f9426f8373b9403d7c57705219', 'AcousticMatch_v3.1', '2025-11-14 22:49:18'),
(6007, 1007, 'f4e1f74f762f4b74e1d3e11079979b0c7444c5f9426f8373b9403d7c57705219', 'AcousticMatch_v3.1', '2025-11-13 22:49:18'),
(6008, 1008, '585093138b3074092497645d9b5006b432a9c37920154e17e812f8626c997321', 'AcousticMatch_v3.1', '2025-11-05 22:49:18'),
(6009, 1009, 'a7ef1d8977c844979e2c6af9429542a370fa72718e244d038f4d2215f75e812f', 'AcousticMatch_v3.1', '2025-11-04 22:49:18'),
(6010, 1010, '079979b0c7444c5f9426f8373b9403d7c5770521943c2c7d949cf9d2466ef4b14', 'AcousticMatch_v3.1', '2025-11-01 22:49:18'),
(6011, 1011, 'f4e1f74f762f4b74e1d3e11079979b0c7444c5f9426f8373b9403d7c57705219', 'AcousticMatch_v3.1', '2025-11-02 22:49:18'),
(6012, 1012, '4d7a83d3600c436fb247d487210c326b48472f8626c997321356e72b03d641c8', 'AcousticMatch_v3.1', '2025-11-11 22:49:18'),
(6013, 1013, '521943c2c7d949cf9d2466ef4b148d8b563c7849938830fe41718ec490c0a91e', 'AcousticMatch_v3.1', '2025-11-05 22:49:18'),
(6014, 1014, '58c5a242c7af4711818a7c2c9de182372545d9472fb8b21c430e35309d435532', 'AcousticMatch_v3.1', '2025-11-13 22:49:18'),
(6015, 1015, '7e812f8626c997321356e72b03d641c88147d3c01b9c71a39f67a42ec86a34795', 'AcousticMatch_v3.1', '2025-11-02 22:49:18'),
(6016, 1016, '3b593630f6584210a48d8b563c7849938830fe41718ec490c0a91e4f48483c74', 'AcousticMatch_v3.1', '2025-11-07 22:49:18'),
(6017, 1017, 'f4e1f74f762f4b74e1d3e11079979b0c7444c5f9426f8373b9403d7c57705219', 'AcousticMatch_v3.1', '2025-11-09 22:49:18'),
(6018, 1018, '4d7a83d3600c436fb247d487210c326b48472f8626c997321356e72b03d641c8', 'AcousticMatch_v3.1', '2025-11-14 22:49:18'),
(6019, 1019, '3b593630f6584210a48d8b563c7849938830fe41718ec490c0a91e4f48483c74', 'AcousticMatch_v3.1', '2025-11-06 22:49:18'),
(6020, 1020, '12f205a109964580b080cc9074092497645d9b5006b432a9c37920154e17e812', 'AcousticMatch_v3.1', '2025-11-12 22:49:18'),
(6021, 1021, '6a27e948c27943f2908f5127d498175d03a1103f7e812f8626c997321356e72b', 'AcousticMatch_v3.1', '2025-11-05 22:49:18'),
(6022, 1022, '375276e0ef0042f0b484501a37a7ef1d8977c844979e2c6af9429542a370fa72', 'AcousticMatch_v3.1', '2025-11-06 22:49:18'),
(6023, 1023, 'f4e1f74f762f4b74e1d3e11079979b0c7444c5f9426f8373b9403d7c57705219', 'AcousticMatch_v3.1', '2025-11-10 22:49:18'),
(6024, 1024, '4d7a83d3600c436fb247d487210c326b48472f8626c997321356e72b03d641c8', 'AcousticMatch_v3.1', '2025-11-03 22:49:18'),
(6025, 1025, '3b593630f6584210a48d8b563c7849938830fe41718ec490c0a91e4f48483c74', 'AcousticMatch_v3.1', '2025-11-11 22:49:18'),
(6026, 1026, '12f205a109964580b080cc9074092497645d9b5006b432a9c37920154e17e812', 'AcousticMatch_v3.1', '2025-11-12 22:49:18'),
(6027, 1027, '58c5a242c7af4711818a7c2c9de182372545d9472fb8b21c430e35309d435532', 'AcousticMatch_v3.1', '2025-11-09 22:49:18'),
(6028, 1028, '521943c2c7d949cf9d2466ef4b148d8b563c7849938830fe41718ec490c0a91e', 'AcousticMatch_v3.1', '2025-11-07 22:49:18'),
(6029, 1029, '6a27e948c27943f2908f5127d498175d03a1103f7e812f8626c997321356e72b', 'AcousticMatch_v3.1', '2025-11-14 22:49:18'),
(6030, 1030, '375276e0ef0042f0b484501a37a7ef1d8977c844979e2c6af9429542a370fa72', 'AcousticMatch_v3.1', '2025-11-08 22:49:18'),
(6031, 1031, 'f4e1f74f762f4b74e1d3e11079979b0c7444c5f9426f8373b9403d7c57705219', 'AcousticMatch_v3.1', '2025-11-05 22:49:18'),
(6032, 1032, '4d7a83d3600c436fb247d487210c326b48472f8626c997321356e72b03d641c8', 'AcousticMatch_v3.1', '2025-11-11 22:49:18'),
(6033, 1033, '3b593630f6584210a48d8b563c7849938830fe41718ec490c0a91e4f48483c74', 'AcousticMatch_v3.1', '2025-11-15 22:49:18'),
(6034, 1034, '12f205a109964580b080cc9074092497645d9b5006b432a9c37920154e17e812', 'AcousticMatch_v3.1', '2025-11-09 22:49:18'),
(6035, 1035, '58c5a242c7af4711818a7c2c9de182372545d9472fb8b21c430e35309d435532', 'AcousticMatch_v3.1', '2025-11-03 22:49:18'),
(6036, 1036, '521943c2c7d949cf9d2466ef4b148d8b563c7849938830fe41718ec490c0a91e', 'AcousticMatch_v3.1', '2025-11-13 22:49:18'),
(6037, 1037, '6a27e948c27943f2908f5127d498175d03a1103f7e812f8626c997321356e72b', 'AcousticMatch_v3.1', '2025-11-06 22:49:18'),
(6038, 1038, '375276e0ef0042f0b484501a37a7ef1d8977c844979e2c6af9429542a370fa72', 'AcousticMatch_v3.1', '2025-11-04 22:49:18'),
(6039, 1039, 'f4e1f74f762f4b74e1d3e11079979b0c7444c5f9426f8373b9403d7c57705219', 'AcousticMatch_v3.1', '2025-11-07 22:49:18'),
(6040, 1040, '4d7a83d3600c436fb247d487210c326b48472f8626c997321356e72b03d641c8', 'AcousticMatch_v3.1', '2025-11-14 22:49:18');

-- Insert into user_requests
INSERT INTO user_requests (request_id, user_input, detected_intent, agent_used, song_id, response_summary, timestamp) VALUES
(7001, 'Tell me about the song "Zahrat El Mada''en" by Fairuz and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1001, 'Provided summary including genre (Classical Arabic/Tarab) and mood (Somber/Patriotic) and cultural notes.', '2025-11-17 21:49:18'),
(7002, 'Tell me about the song "Fairuz - Derived Track 1 (Waltz)" by Fairuz and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1002, 'Provided summary including genre (Waltz) and mood (Calm) and cultural notes.', '2025-11-17 22:28:18'),
(7003, 'Tell me about the song "Fairuz - Derived Track 2 (Classical Instrumental)" by Fairuz and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1003, 'Provided summary including genre (Classical Instrumental) and mood (Calm) and cultural notes.', '2025-11-17 22:31:18'),
(7004, 'Tell me about the song "Fairuz - Derived Track 3 (Tarab)" by Fairuz and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1004, 'Provided summary including genre (Tarab) and mood (Neutral) and cultural notes.', '2025-11-17 22:35:18'),
(7005, 'Tell me about the song "Ya Tabtab Wa Dalaa" by Nancy Ajram and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1005, 'Provided summary including genre (Arabic Pop/Dance) and mood (Happy/Flirty) and cultural notes.', '2025-11-17 22:15:18'),
(7006, 'Tell me about the song "Nancy Ajram - Derived Track 1 (Club Pop)" by Nancy Ajram and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1006, 'Provided summary including genre (Club Pop) and mood (Vibrant) and cultural notes.', '2025-11-17 22:37:18'),
(7007, 'Tell me about the song "Nancy Ajram - Derived Track 2 (Pop Dance)" by Nancy Ajram and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1007, 'Provided summary including genre (Pop Dance) and mood (Vibrant) and cultural notes.', '2025-11-17 22:42:18'),
(7008, 'Tell me about the song "Nancy Ajram - Derived Track 3 (Electronic Remix)" by Nancy Ajram and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1008, 'Provided summary including genre (Electronic Remix) and mood (Happy/Flirty) and cultural notes.', '2025-11-17 22:12:18'),
(7009, 'Tell me about the song "Raksit Leila" by Mashrou'' Leila and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1009, 'Provided summary including genre (Indie Rock/Alternative) and mood (Intense/Rebellious) and cultural notes.', '2025-11-17 22:20:18'),
(7010, 'Tell me about the song "Mashrou'' Leila - Derived Track 1 (Punk Revival)" by Mashrou'' Leila and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1010, 'Provided summary including genre (Punk Revival) and mood (Intense/Rebellious) and cultural notes.', '2025-11-17 22:34:18'),
(7011, 'Tell me about the song "Mashrou'' Leila - Derived Track 2 (Alternative Ballad)" by Mashrou'' Leila and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1011, 'Provided summary including genre (Alternative Ballad) and mood (Calm) and cultural notes.', '2025-11-17 22:40:18'),
(7012, 'Tell me about the song "Mashrou'' Leila - Derived Track 3 (Art Rock)" by Mashrou'' Leila and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1012, 'Provided summary including genre (Art Rock) and mood (Intense/Rebellious) and cultural notes.', '2025-11-17 22:48:18'),
(7013, 'Tell me about the song "Ma Fi Law" by Wael Kfoury and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1013, 'Provided summary including genre (Romantic Pop) and mood (Romantic/Longing) and cultural notes.', '2025-11-17 22:41:18'),
(7014, 'Tell me about the song "Wael Kfoury - Derived Track 1 (Acoustic Cover)" by Wael Kfoury and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1014, 'Provided summary including genre (Acoustic Cover) and mood (Romantic/Longing) and cultural notes.', '2025-11-17 22:29:18'),
(7015, 'Tell me about the song "Wael Kfoury - Derived Track 2 (Mid-Tempo Pop)" by Wael Kfoury and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1015, 'Provided summary including genre (Mid-Tempo Pop) and mood (Vibrant) and cultural notes.', '2025-11-17 22:04:18'),
(7016, 'Tell me about the song "Wael Kfoury - Derived Track 3 (Pop Ballad)" by Wael Kfoury and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1016, 'Provided summary including genre (Pop Ballad) and mood (Romantic/Longing) and cultural notes.', '2025-11-17 22:46:18'),
(7017, 'Tell me about the song "Betmoun" by Elissa and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1017, 'Provided summary including genre (Arabic Ballad) and mood (Emotional/Mellow) and cultural notes.', '2025-11-17 22:36:18'),
(7018, 'Tell me about the song "Elissa - Derived Track 1 (Acoustic Ballad)" by Elissa and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1018, 'Provided summary including genre (Acoustic Ballad) and mood (Neutral) and cultural notes.', '2025-11-17 22:33:18'),
(7019, 'Tell me about the song "Elissa - Derived Track 2 (Orchestral Pop)" by Elissa and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1019, 'Provided summary including genre (Orchestral Pop) and mood (Emotional/Mellow) and cultural notes.', '2025-11-17 22:40:18'),
(7020, 'Tell me about the song "Elissa - Derived Track 3 (Mellow Pop)" by Elissa and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1020, 'Provided summary including genre (Mellow Pop) and mood (Emotional/Mellow) and cultural notes.', '2025-11-17 22:27:18'),
(7021, 'Tell me about the song "Albi Asheqha" by Ragheb Alama and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1021, 'Provided summary including genre (Upbeat Pop/Dance) and mood (Celebratory/Driving) and cultural notes.', '2025-11-17 22:48:18'),
(7022, 'Tell me about the song "Ragheb Alama - Derived Track 1 (Eurodance)" by Ragheb Alama and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1022, 'Provided summary including genre (Eurodance) and mood (Celebratory/Driving) and cultural notes.', '2025-11-17 22:47:18'),
(7023, 'Tell me about the song "Ragheb Alama - Derived Track 2 (Summer Hit)" by Ragheb Alama and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1023, 'Provided summary including genre (Summer Hit) and mood (Neutral) and cultural notes.', '2025-11-17 22:37:18'),
(7024, 'Tell me about the song "Ragheb Alama - Derived Track 3 (Pop Funk)" by Ragheb Alama and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1024, 'Provided summary including genre (Pop Funk) and mood (Celebratory/Driving) and cultural notes.', '2025-11-17 21:55:18'),
(7025, 'Tell me about the song "Ya Tayr" by Assi El Hallani and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1025, 'Provided summary including genre (Folk Pop/Dabke) and mood (Traditional/Energetic) and cultural notes.', '2025-11-17 22:17:18'),
(7026, 'Tell me about the song "Assi El Hallani - Derived Track 1 (Folk Dance)" by Assi El Hallani and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1026, 'Provided summary including genre (Folk Dance) and mood (Traditional/Energetic) and cultural notes.', '2025-11-17 22:36:18'),
(7027, 'Tell me about the song "Assi El Hallani - Derived Track 2 (Traditional Instrumental)" by Assi El Hallani and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1027, 'Provided summary including genre (Traditional Instrumental) and mood (Vibrant) and cultural notes.', '2025-11-17 22:10:18'),
(7028, 'Tell me about the song "Assi El Hallani - Derived Track 3 (World Fusion)" by Assi El Hallani and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1028, 'Provided summary including genre (World Fusion) and mood (Traditional/Energetic) and cultural notes.', '2025-11-17 22:21:18'),
(7029, 'Tell me about the song "Bema Enno" by Ziad Rahbani and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1029, 'Provided summary including genre (Jazz/Experimental) and mood (Witty/Cynical) and cultural notes.', '2025-11-17 22:07:18'),
(7030, 'Tell me about the song "Ziad Rahbani - Derived Track 1 (Bossa Nova)" by Ziad Rahbani and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1030, 'Provided summary including genre (Bossa Nova) and mood (Neutral) and cultural notes.', '2025-11-17 22:05:18'),
(7031, 'Tell me about the song "Ziad Rahbani - Derived Track 2 (Instrumental Jam)" by Ziad Rahbani and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1031, 'Provided summary including genre (Instrumental Jam) and mood (Calm) and cultural notes.', '2025-11-17 22:24:18'),
(7032, 'Tell me about the song "Ziad Rahbani - Derived Track 3 (Fusion Jazz)" by Ziad Rahbani and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1032, 'Provided summary including genre (Fusion Jazz) and mood (Witty/Cynical) and cultural notes.', '2025-11-17 22:42:18'),
(7033, 'Tell me about the song "Mutafarriqah" by Majida El Roumi and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1033, 'Provided summary including genre (Tarab/Orchestral) and mood (Epic/Dramatic) and cultural notes.', '2025-11-17 22:16:18'),
(7034, 'Tell me about the song "Majida El Roumi - Derived Track 1 (Dramatic Ballad)" by Majida El Roumi and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1034, 'Provided summary including genre (Dramatic Ballad) and mood (Epic/Dramatic) and cultural notes.', '2025-11-17 22:32:18'),
(7035, 'Tell me about the song "Majida El Roumi - Derived Track 2 (Symphonic)" by Majida El Roumi and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1035, 'Provided summary including genre (Symphonic) and mood (Epic/Dramatic) and cultural notes.', '2025-11-17 22:03:18'),
(7036, 'Tell me about the song "Majida El Roumi - Derived Track 3 (Film Score)" by Majida El Roumi and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1036, 'Provided summary including genre (Film Score) and mood (Neutral) and cultural notes.', '2025-11-17 22:47:18'),
(7037, 'Tell me about the song "Passport" by Marcel Khalife and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1037, 'Provided summary including genre (Folk/Oud/Political) and mood (Political/Acoustic) and cultural notes.', '2025-11-17 22:07:18'),
(7038, 'Tell me about the song "Marcel Khalife - Derived Track 1 (Poetry Recital)" by Marcel Khalife and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1038, 'Provided summary including genre (Poetry Recital) and mood (Political/Acoustic) and cultural notes.', '2025-11-17 22:23:18'),
(7039, 'Tell me about the song "Marcel Khalife - Derived Track 2 (Instrumental Medley)" by Marcel Khalife and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1039, 'Provided summary including genre (Instrumental Medley) and mood (Calm) and cultural notes.', '2025-11-17 22:26:18'),
(7040, 'Tell me about the song "Marcel Khalife - Derived Track 3 (Acoustic Folk)" by Marcel Khalife and its cultural impact.', 'Query_Song_Context', 'InfoBot_V2', 1040, 'Provided summary including genre (Acoustic Folk) and mood (Political/Acoustic) and cultural notes.', '2025-11-17 22:49:18');

-- Insert into recommendations_log
INSERT INTO recommendations_log (rec_id, user_id, song_id, reason, confidence_score, timestamp) VALUES
(8001, 'user_5866', 1001, 'High similarity in BPM, Classical Arabic/Tarab and somber/patriotic to user''s recent listens.', 0.817, '2025-11-17 19:49:18'),
(8002, 'user_3436', 1002, 'High similarity in BPM, Waltz and calm to user''s recent listens.', 0.963, '2025-11-17 07:49:18'),
(8003, 'user_4193', 1003, 'High similarity in BPM, Classical Instrumental and calm to user''s recent listens.', 0.887, '2025-11-17 10:49:18'),
(8004, 'user_5395', 1004, 'High similarity in BPM, Tarab and neutral to user''s recent listens.', 0.849, '2025-11-17 03:49:18'),
(8005, 'user_1170', 1005, 'High similarity in BPM, Arabic Pop/Dance and happy/flirty to user''s recent listens.', 0.923, '2025-11-17 06:49:18'),
(8006, 'user_6396', 1006, 'High similarity in BPM, Club Pop and vibrant to user''s recent listens.', 0.835, '2025-11-17 01:49:18'),
(8007, 'user_2429', 1007, 'High similarity in BPM, Pop Dance and vibrant to user''s recent listens.', 0.908, '2025-11-17 09:49:18'),
(8008, 'user_1328', 1008, 'High similarity in BPM, Electronic Remix and happy/flirty to user''s recent listens.', 0.825, '2025-11-17 19:49:18'),
(8009, 'user_4193', 1009, 'High similarity in BPM, Indie Rock/Alternative and intense/rebellious to user''s recent listens.', 0.942, '2025-11-17 08:49:18'),
(8010, 'user_5914', 1010, 'High similarity in BPM, Punk Revival and intense/rebellious to user''s recent listens.', 0.899, '2025-11-17 14:49:18'),
(8011, 'user_7737', 1012, 'High similarity in BPM, Art Rock and intense/rebellious to user''s recent listens.', 0.824, '2025-11-17 08:49:18'),
(8012, 'user_5914', 1013, 'High similarity in BPM, Romantic Pop and romantic/longing to user''s recent listens.', 0.848, '2025-11-17 15:49:18'),
(8013, 'user_1170', 1014, 'High similarity in BPM, Acoustic Cover and romantic/longing to user''s recent listens.', 0.908, '2025-11-17 12:49:18'),
(8014, 'user_4193', 1015, 'High similarity in BPM, Mid-Tempo Pop and vibrant to user''s recent listens.', 0.871, '2025-11-17 16:49:18'),
(8015, 'user_4193', 1016, 'High similarity in BPM, Pop Ballad and romantic/longing to user''s recent listens.', 0.902, '2025-11-17 13:49:18'),
(8016, 'user_1328', 1017, 'High similarity in BPM, Arabic Ballad and emotional/mellow to user''s recent listens.', 0.864, '2025-11-17 09:49:18'),
(8017, 'user_5866', 1018, 'High similarity in BPM, Acoustic Ballad and neutral to user''s recent listens.', 0.938, '2025-11-17 15:49:18'),
(8018, 'user_6396', 1019, 'High similarity in BPM, Orchestral Pop and emotional/mellow to user''s recent listens.', 0.970, '2025-11-17 11:49:18'),
(8019, 'user_3436', 1020, 'High similarity in BPM, Mellow Pop and emotional/mellow to user''s recent listens.', 0.887, '2025-11-17 06:49:18'),
(8020, 'user_2429', 1021, 'High similarity in BPM, Upbeat Pop/Dance and celebratory/driving to user''s recent listens.', 0.933, '2025-11-17 13:49:18'),
(8021, 'user_5395', 1022, 'High similarity in BPM, Eurodance and celebratory/driving to user''s recent listens.', 0.957, '2025-11-17 15:49:18'),
(8022, 'user_7737', 1023, 'High similarity in BPM, Summer Hit and neutral to user''s recent listens.', 0.898, '2025-11-17 03:49:18'),
(8023, 'user_4193', 1024, 'High similarity in BPM, Pop Funk and celebratory/driving to user''s recent listens.', 0.941, '2025-11-17 07:49:18'),
(8024, 'user_5914', 1025, 'High similarity in BPM, Folk Pop/Dabke and traditional/energetic to user''s recent listens.', 0.909, '2025-11-17 00:49:18'),
(8025, 'user_5866', 1026, 'High similarity in BPM, Folk Dance and traditional/energetic to user''s recent listens.', 0.882, '2025-11-17 05:49:18'),
(8026, 'user_1170', 1027, 'High similarity in BPM, Traditional Instrumental and vibrant to user''s recent listens.', 0.830, '2025-11-17 10:49:18'),
(8027, 'user_6396', 1028, 'High similarity in BPM, World Fusion and traditional/energetic to user''s recent listens.', 0.923, '2025-11-17 18:49:18'),
(8028, 'user_2429', 1029, 'High similarity in BPM, Jazz/Experimental and witty/cynical to user''s recent listens.', 0.963, '2025-11-17 12:49:18'),
(8029, 'user_5395', 1030, 'High similarity in BPM, Bossa Nova and neutral to user''s recent listens.', 0.835, '2025-11-17 02:49:18'),
(8030, 'user_7737', 1031, 'High similarity in BPM, Instrumental Jam and calm to user''s recent listens.', 0.959, '2025-11-17 14:49:18'),
(8031, 'user_1328', 1033, 'High similarity in BPM, Tarab/Orchestral and epic/dramatic to user''s recent listens.', 0.886, '2025-11-17 21:49:18'),
(8032, 'user_5866', 1034, 'High similarity in BPM, Dramatic Ballad and epic/dramatic to user''s recent listens.', 0.803, '2025-11-17 16:49:18'),
(8033, 'user_4193', 1035, 'High similarity in BPM, Symphonic and epic/dramatic to user''s recent listens.', 0.985, '2025-11-17 17:49:18'),
(8034, 'user_5914', 1037, 'High similarity in BPM, Folk/Oud/Political and political/acoustic to user''s recent listens.', 0.881, '2025-11-17 00:49:18'),
(8035, 'user_6396', 1038, 'High similarity in BPM, Poetry Recital and political/acoustic to user''s recent listens.', 0.916, '2025-11-17 17:49:18'),
(8036, 'user_2429', 1039, 'High similarity in BPM, Instrumental Medley and calm to user''s recent listens.', 0.897, '2025-11-17 21:49:18'),
(8037, 'user_5395', 1040, 'High similarity in BPM, Acoustic Folk and political/acoustic to user''s recent listens.', 0.844, '2025-11-17 04:49:18');

