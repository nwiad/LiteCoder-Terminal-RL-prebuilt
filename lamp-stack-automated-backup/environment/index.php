<?php
// E-Commerce Application - Main Page
$pageTitle = "Welcome to Our Store";

require_once 'config.php';

try {
    $pdo = new PDO(
        "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME,
        DB_USER,
        DB_PASS
    );
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    $stmt = $pdo->query("SELECT COUNT(*) as total FROM customers");
    $customerCount = $stmt->fetch(PDO::FETCH_ASSOC)['total'];

    $stmt = $pdo->query("SELECT SUM(amount) as revenue FROM orders");
    $totalRevenue = $stmt->fetch(PDO::FETCH_ASSOC)['revenue'];
} catch (PDOException $e) {
    $customerCount = 0;
    $totalRevenue = 0;
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title><?php echo $pageTitle; ?></title>
</head>
<body>
    <h1><?php echo $pageTitle; ?></h1>
    <p>Total Customers: <?php echo $customerCount; ?></p>
    <p>Total Revenue: $<?php echo number_format($totalRevenue, 2); ?></p>
</body>
</html>
