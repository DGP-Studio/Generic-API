SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `dgpstudio_generic_api`
--

-- --------------------------------------------------------

--
-- Table structure for table `avatar_strategies`
--

CREATE TABLE `avatar_strategies` (
  `id` int NOT NULL,
  `avatar_id` int NOT NULL,
  `mys_strategy_id` int DEFAULT NULL,
  `hoyolab_strategy_id` int DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `avatar_strategies`
--

INSERT INTO `avatar_strategies` (`id`, `avatar_id`, `mys_strategy_id`, `hoyolab_strategy_id`) VALUES
(1, 10000087, 351, 730),
(2, 10000047, 152, 189),
(3, 10000094, 378, 973),
(4, 10000057, 211, 165),
(5, 10000051, 127, 214),
(6, 10000058, 220, 161),
(7, 10000026, 78, 198),
(8, 10000093, 372, 938),
(9, 10000092, 371, 939),
(10, 10000073, 264, 156),
(11, 10000052, 187, 171),
(12, 10000049, 182, 157),
(13, 10000090, 369, 914),
(14, 10000091, 366, 913),
(15, 10000002, 175, 188),
(16, 10000071, 257, 179),
(17, 10000066, 225, 172),
(18, 10000089, 359, 892),
(19, 10000082, 312, 428),
(20, 10000088, 358, 893),
(21, 10000086, 356, 744),
(22, 10000022, 73, 212),
(23, 10000046, 77, 199),
(24, 10000030, 81, 223),
(25, 10000033, 89, 162),
(26, 10000084, 339, 705),
(27, 10000060, 236, 224),
(28, 10000083, 340, 706),
(29, 10000054, 196, 190),
(30, 10000075, 272, 169),
(31, 10000029, 75, 211),
(32, 10000078, 290, 228),
(33, 10000070, 261, 180),
(34, 10000063, 215, 195),
(35, 10000079, 301, 246),
(36, 10000037, 79, 197),
(37, 10000069, 248, 178),
(38, 10000038, 61, 207),
(39, 10000062, 191, 227),
(40, 10000035, 83, 196),
(41, 10000042, 82, 200),
(42, 10000016, 70, 209),
(43, 10000041, 63, 208),
(44, 10000003, 109, 213),
(45, 10000007, 90, NULL),
(46, 10000081, 311, 429),
(47, 10000085, 349, 725),
(48, 10000025, 106, 217),
(49, 10000065, 238, 193),
(50, 10000076, 273, 170),
(51, 10000061, 315, 434),
(52, 10000055, 212, 167),
(53, 10000077, 289, 230),
(54, 10000080, 304, 402),
(55, 10000074, 270, 181),
(56, 10000072, 256, 185),
(57, 10000067, 247, 183),
(58, 10000068, 254, 184),
(59, 10000059, 241, 192),
(60, 10000027, 88, 215),
(61, 10000050, 202, 225),
(62, 10000056, 188, 194),
(63, 10000064, 216, 216),
(64, 10000045, 104, 206),
(65, 10000053, 183, 226),
(66, 10000020, 74, 160),
(67, 10000031, 65, 186),
(68, 10000032, 110, 202),
(69, 10000048, 116, 221),
(70, 10000036, 84, 222),
(71, 10000014, 71, 182),
(72, 10000039, 62, 204),
(73, 10000043, 64, 203),
(74, 10000034, 66, 159),
(75, 10000015, 69, 205),
(76, 10000044, 80, 219),
(77, 10000023, 86, 220),
(78, 10000024, 87, 218),
(79, 10000021, 111, 201),
(80, 10000006, 184, 187);

-- --------------------------------------------------------

--
-- Table structure for table `wallpapers`
--

CREATE TABLE `wallpapers` (
  `id` int NOT NULL,
  `url` text NOT NULL,
  `display_date` date DEFAULT NULL,
  `last_display_date` date DEFAULT NULL,
  `source_url` text NOT NULL,
  `author` text NOT NULL,
  `uploader` text NOT NULL,
  `disabled` tinyint NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `wallpapers`
--

INSERT INTO `wallpapers` (`id`, `url`, `display_date`, `last_display_date`, `source_url`, `author`, `uploader`, `disabled`) VALUES
(1, 'https://img.alicdn.com/imgextra/i3/1797064093/O1CN01OYeLmJ1g6e1QuzRKm_!!1797064093.jpg', NULL, NULL, 'https://img.alicdn.com/imgextra/i3/1797064093/O1CN01OYeLmJ1g6e1QuzRKm_!!1797064093.jpg', 'random author', 'sample uploader', 0),
(2, 'https://img.alicdn.com/imgextra/i4/1797064093/O1CN01OWQeuC1g6e1OrwG1P_!!1797064093.png', NULL, NULL, 'https://img.alicdn.com/imgextra/i4/1797064093/O1CN01OWQeuC1g6e1OrwG1P_!!1797064093.png', 'MiHoYo', 'Snap Hutao', 0);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `avatar_strategies`
--
ALTER TABLE `avatar_strategies`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `avatar_id` (`avatar_id`) USING BTREE,
  ADD KEY `mys_strategy_id` (`mys_strategy_id`),
  ADD KEY `hoyolab_strategy_id` (`hoyolab_strategy_id`);

--
-- Indexes for table `wallpapers`
--
ALTER TABLE `wallpapers`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `avatar_strategies`
--
ALTER TABLE `avatar_strategies`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=160;

--
-- AUTO_INCREMENT for table `wallpapers`
--
ALTER TABLE `wallpapers`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
