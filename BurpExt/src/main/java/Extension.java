import burp.api.montoya.BurpExtension;
import burp.api.montoya.MontoyaApi;
import burp.api.montoya.http.handler.*;
import burp.api.montoya.logging.Logging;

import javax.swing.*;
import java.awt.*;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.concurrent.CompletableFuture;

public class Extension implements BurpExtension {

    private MontoyaApi api;
    private Logging logging;
    private HttpClient httpClient;
    private String targetUrl = "http://localhost:5000";
    private JTextField serverAddressField;
    private JLabel statusLabel;

    @Override
    public void initialize(MontoyaApi api) {
        this.api = api;
        this.logging = api.logging();
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(10))
                .build();

        // Set extension name
        api.extension().setName("IDOR Killer");

        // Create and register the settings panel
        JComponent settingsPanel = createSettingsPanel();
        api.userInterface().registerSuiteTab("IDOR Killer", settingsPanel);

        // Register HTTP handler to capture all HTTP traffic
        api.http().registerHttpHandler(new HttpHandler() {
            @Override
            public RequestToBeSentAction handleHttpRequestToBeSent(HttpRequestToBeSent requestToBeSent) {
                // We don't need to modify the request
                return RequestToBeSentAction.continueWith(requestToBeSent);
            }

            @Override
            public ResponseReceivedAction handleHttpResponseReceived(HttpResponseReceived responseReceived) {
                // Process the request/response pair when response is received
                CompletableFuture.runAsync(() -> {
                    try {
                        // Skip if it's a JS/CSS file
                        if (!shouldFilterOut(responseReceived)) {
                            sendToProcessingServer(responseReceived);
                        }
                    } catch (Exception e) {
                        logging.logToError("Failed to send data to server: " + e.getMessage());
                    }
                });

                // Return the response unmodified
                return ResponseReceivedAction.continueWith(responseReceived);
            }
        });

        // Log initialization
        logging.logToOutput("Extension loaded successfully");
        logging.logToOutput("Monitoring HTTP traffic and forwarding to processing server...");
    }

    private JComponent createSettingsPanel() {
        JPanel mainPanel = new JPanel();
        mainPanel.setLayout(new BorderLayout(10, 10));
        mainPanel.setBorder(BorderFactory.createEmptyBorder(20, 20, 20, 20));

        // Title panel
        JPanel titlePanel = new JPanel(new FlowLayout(FlowLayout.LEFT));
        JLabel titleLabel = new JLabel("IDOR Killer Settings");
        titleLabel.setFont(new Font("Arial", Font.BOLD, 16));
        titlePanel.add(titleLabel);
        mainPanel.add(titlePanel, BorderLayout.NORTH);

        // Settings panel
        JPanel settingsPanel = new JPanel();
        settingsPanel.setLayout(new BoxLayout(settingsPanel, BoxLayout.Y_AXIS));
        settingsPanel.setBorder(BorderFactory.createEmptyBorder(10, 0, 10, 0));

        // Server address setting
        JPanel serverPanel = new JPanel(new FlowLayout(FlowLayout.LEFT));
        JLabel serverLabel = new JLabel("Processing Server Address:");
        serverLabel.setPreferredSize(new Dimension(200, 25));
        serverAddressField = new JTextField(targetUrl, 30);
        serverAddressField.setToolTipText("Enter the URL of your processing server (e.g., http://localhost:3000)");

        JButton updateButton = new JButton("Update");
        updateButton.addActionListener(e -> updateServerAddress());

        serverPanel.add(serverLabel);
        serverPanel.add(serverAddressField);
        serverPanel.add(updateButton);
        settingsPanel.add(serverPanel);

        // Status panel
        JPanel statusPanel = new JPanel(new FlowLayout(FlowLayout.LEFT));
        statusLabel = new JLabel("Status: Ready");
        statusLabel.setForeground(new Color(0, 128, 0));
        statusPanel.add(statusLabel);
        settingsPanel.add(statusPanel);

        // Info panel
        JPanel infoPanel = new JPanel();
        infoPanel.setLayout(new BoxLayout(infoPanel, BoxLayout.Y_AXIS));
        infoPanel.setBorder(BorderFactory.createTitledBorder("Information"));

        JTextArea infoText = new JTextArea();
        infoText.setEditable(false);
        infoText.setBackground(mainPanel.getBackground());
        infoText.setText(
                "This extension monitors Burp Suite's proxy history and forwards raw HTTP\n" +
                        "request/response pairs to your configured processing server.\n\n" +
                        "Features:\n" +
                        "• Automatically detects new proxy history entries\n" +
                        "• Filters out JavaScript and CSS files\n" +
                        "• Sends data as JSON POST requests\n\n" +
                        "The server will receive JSON with the following structure:\n" +
                        "{\n" +
                        "  \"request\": \"<raw HTTP request>\",\n" +
                        "  \"response\": \"<raw HTTP response>\",\n" +
                        "  \"timestamp\": <milliseconds>\n" +
                        "}"
        );
        infoText.setFont(new Font("Monospaced", Font.PLAIN, 12));
        infoPanel.add(infoText);

        mainPanel.add(settingsPanel, BorderLayout.CENTER);
        mainPanel.add(infoPanel, BorderLayout.SOUTH);

        return mainPanel;
    }

    private void updateServerAddress() {
        String newAddress = serverAddressField.getText().trim();

        if (newAddress.isEmpty()) {
            statusLabel.setText("Status: Error - Address cannot be empty");
            statusLabel.setForeground(Color.RED);
            logging.logToError("Server address cannot be empty");
            return;
        }

        // Basic URL validation
        try {
            URI uri = URI.create(newAddress);

            // Show testing status
            statusLabel.setText("Status: Testing connection...");
            statusLabel.setForeground(new Color(255, 140, 0)); // Orange color
            serverAddressField.setEnabled(false);

            // Test connection in background thread to avoid blocking UI
            new Thread(() -> {
                boolean connectionSuccess = testConnection(newAddress);

                // Update UI on success or failure
                SwingUtilities.invokeLater(() -> {
                    serverAddressField.setEnabled(true);

                    if (connectionSuccess) {
                        targetUrl = newAddress;
                        statusLabel.setText("Status: Server address updated successfully");
                        statusLabel.setForeground(new Color(0, 128, 0));
                        logging.logToOutput("Processing server address updated to: " + targetUrl);
                    } else {
                        statusLabel.setText("Status: Error - Cannot connect to server");
                        statusLabel.setForeground(Color.RED);
                        logging.logToError("Failed to connect to server: " + newAddress);
                    }
                });
            }).start();

        } catch (IllegalArgumentException e) {
            statusLabel.setText("Status: Error - Invalid URL format");
            statusLabel.setForeground(Color.RED);
            logging.logToError("Invalid server address format: " + e.getMessage());
        }
    }

    private boolean testConnection(String serverAddress) {
        try {
            // Create a simple test request to check if server is reachable
            HttpRequest testRequest = HttpRequest.newBuilder()
                    .uri(URI.create(serverAddress))
                    .header("Content-Type", "application/json")
                    .header("User-Agent", "BurpSuite-IDOR-Killer/1.0")
                    .POST(HttpRequest.BodyPublishers.ofString("{\"test\":true}", StandardCharsets.UTF_8))
                    .timeout(Duration.ofSeconds(5))
                    .build();

            HttpResponse<String> response = httpClient.send(testRequest, HttpResponse.BodyHandlers.ofString());

            // Consider 2xx, 4xx, and 5xx as successful connection (server is responding)
            // We only care if the server is reachable, not if it accepts our request
            int statusCode = response.statusCode();
            logging.logToOutput("Connection test response: " + statusCode);
            return statusCode >= 200 && statusCode < 600;

        } catch (IOException e) {
            logging.logToError("Connection test failed - IO Error: " + e.getMessage());
            return false;
        } catch (InterruptedException e) {
            logging.logToError("Connection test interrupted: " + e.getMessage());
            Thread.currentThread().interrupt();
            return false;
        } catch (Exception e) {
            logging.logToError("Connection test failed: " + e.getMessage());
            return false;
        }
    }

    private boolean shouldFilterOut(HttpResponseReceived responseReceived) {
        try {
            // Get URL path
            String url = responseReceived.initiatingRequest().url().toLowerCase();

            // Filter out common JS library patterns
            if (url.endsWith(".js") || url.endsWith(".min.js") || url.endsWith(".mjs")) {
                logging.logToOutput("Filtered out JS file: " + url);
                return true;
            }

            // Filter out CSS files
            if (url.endsWith(".css") || url.endsWith(".min.css")) {
                logging.logToOutput("Filtered out CSS file: " + url);
                return true;
            }

            // Check Content-Type headers in response
            String contentType = responseReceived.headerValue("Content-Type");
            if (contentType != null) {
                contentType = contentType.toLowerCase();

                // Filter out JavaScript content types
                if (contentType.contains("javascript") ||
                        contentType.contains("application/x-javascript") ||
                        contentType.contains("text/javascript") ||
                        contentType.contains("application/ecmascript")) {
                    logging.logToOutput("Filtered out JS content type: " + url);
                    return true;
                }

                // Filter out CSS content types
                if (contentType.contains("text/css") || contentType.contains("stylesheet")) {
                    logging.logToOutput("Filtered out CSS content type: " + url);
                    return true;
                }
            }

            return false;
        } catch (Exception e) {
            logging.logToError("Error filtering entry: " + e.getMessage());
            return false;
        }
    }

    private void sendToProcessingServer(HttpResponseReceived responseReceived) {
        try {
            // Extract raw request and response
            String rawRequest = responseReceived.initiatingRequest().toString();
            String rawResponse = responseReceived.toString();

            // Create JSON payload
            String jsonPayload = createJsonPayload(rawRequest, rawResponse);

            // Create HTTP request to processing server
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(targetUrl + "/analyze"))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(jsonPayload, StandardCharsets.UTF_8))
                    .timeout(Duration.ofSeconds(30))
                    .build();

            // Send request
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

            // Log success
            logging.logToOutput(String.format("Successfully sent request/response pair to backend server (Status: %d)",
                    response.statusCode()));

        } catch (IOException e) {
            logging.logToError("IO Error sending to server: " + e.getMessage());
        } catch (InterruptedException e) {
            logging.logToError("Request interrupted: " + e.getMessage());
            Thread.currentThread().interrupt();
        } catch (Exception e) {
            logging.logToError("Unexpected error: " + e.getMessage());
        }
    }

    private String createJsonPayload(String rawRequest, String rawResponse) {
        // Escape quotes and newlines for JSON
        String escapedRequest = escapeForJson(rawRequest);
        String escapedResponse = escapeForJson(rawResponse);

        return String.format(
                "{\"request\":\"%s\",\"response\":\"%s\",\"timestamp\":\"%d\"}",
                escapedRequest,
                escapedResponse,
                System.currentTimeMillis()
        );
    }

    private String escapeForJson(String input) {
        if (input == null) return "";

        return input
                .replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t");
    }
}
