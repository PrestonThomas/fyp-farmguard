#include "OV2640.h"
#include <WiFi.h>
#include <WiFiClient.h>
#include "SimStreamer.h"
#include "OV2640Streamer.h"
#include "CRtspSession.h"

#define ENABLE_RTSPSERVER

OV2640 cam;

#ifdef ENABLE_RTSPSERVER
WiFiServer rtspServer(8554);
#endif

#include "wifikeys.h"

void setup()
{
    Serial.begin(115200);
    while (!Serial)
    {
        ;
    }
    cam.init(esp32cam_aithinker_config);

    IPAddress ip;

    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED)
    {
        delay(500);
        Serial.print(F("."));
    }
    ip = WiFi.localIP();
    Serial.println(F("WiFi connected"));
    Serial.println("");
    Serial.println(ip);
    
#ifdef ENABLE_RTSPSERVER
    rtspServer.begin();
#endif
}

CStreamer *streamer;
CRtspSession *session;
WiFiClient client;

void loop()
{
#ifdef ENABLE_RTSPSERVER
    uint32_t msecPerFrame = 100;
    static uint32_t lastimage = millis();

    if(session) {
        session->handleRequests(0);

        uint32_t now = millis();
        if(now > lastimage + msecPerFrame || now < lastimage) {
            session->broadcastCurrentFrame(now);
            lastimage = now;
            now = millis();
            if(now > lastimage + msecPerFrame)
                printf("warning exceeding max frame rate of %d ms\n", now - lastimage);
        }

        if(session->m_stopped) {
            delete session;
            delete streamer;
            session = NULL;
            streamer = NULL;
        }
    }
    else {
        client = rtspServer.accept();

        if(client) {
            streamer = new OV2640Streamer(&client, cam);

            session = new CRtspSession(&client, streamer);
        }
    }
#endif
}
