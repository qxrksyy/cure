import asyncio
import aiohttp
import socket
import sys

LAVALINK_IP = "10.0.0.75"
LAVALINK_PORT = 2333
LAVALINK_PASSWORD = "Confusion10072003$"

async def test_http_connection():
    """Test HTTP connection to Lavalink server"""
    print(f"Testing HTTP connection to {LAVALINK_IP}:{LAVALINK_PORT}...")
    try:
        async with aiohttp.ClientSession() as session:
            # Attempt a version request
            headers = {
                "Authorization": LAVALINK_PASSWORD
            }
            url = f"http://{LAVALINK_IP}:{LAVALINK_PORT}/version"
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    version_info = await response.text()
                    print(f"✅ Lavalink is running! Version info: {version_info}")
                    return True
                else:
                    print(f"❌ Lavalink HTTP request failed with status {response.status}")
                    return False
    except aiohttp.ClientConnectorError as e:
        print(f"❌ Could not connect to Lavalink HTTP API: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing HTTP connection: {e}")
        return False

def test_socket_connection():
    """Basic TCP socket connection test"""
    print(f"Testing socket connection to {LAVALINK_IP}:{LAVALINK_PORT}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((LAVALINK_IP, LAVALINK_PORT))
        sock.close()
        
        if result == 0:
            print(f"✅ Port {LAVALINK_PORT} is open on {LAVALINK_IP}")
            return True
        else:
            print(f"❌ Port {LAVALINK_PORT} is closed on {LAVALINK_IP}")
            return False
    except socket.error as e:
        print(f"❌ Socket error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing socket connection: {e}")
        return False

async def main():
    print("Lavalink Connection Test Utility")
    print("================================\n")
    
    # Test basic socket connection
    socket_result = test_socket_connection()
    
    # Test HTTP connection if socket is open
    if socket_result:
        http_result = await test_http_connection()
        
        if http_result:
            print("\n✅ SUCCESS: Lavalink server is accessible!")
            print("Your bot should be able to connect to it.")
        else:
            print("\n⚠️ WARNING: Lavalink server port is open but HTTP request failed.")
            print("This could be due to incorrect password or configuration.")
    else:
        print("\n❌ FAILED: Cannot connect to Lavalink server.")
        print("Possible reasons:")
        print("  1. Lavalink is not running on the Raspberry Pi")
        print("  2. A firewall is blocking the connection")
        print("  3. The IP address or port is incorrect")
        print("  4. Network connectivity issues between this machine and the Raspberry Pi")
        
        # Try to ping the server
        print("\nAttempting to ping the server...")
        try:
            import subprocess
            ping_process = subprocess.run(["ping", "-n", "4", LAVALINK_IP], 
                                        stdout=subprocess.PIPE, 
                                        stderr=subprocess.PIPE,
                                        text=True)
            print(ping_process.stdout)
            
            if ping_process.returncode == 0:
                print("✅ Ping successful. The Raspberry Pi is reachable.")
                print("   The issue is likely with Lavalink not running or listening on the correct port.")
            else:
                print("❌ Ping failed. Cannot reach the Raspberry Pi.")
                print("   Check network connectivity and if the IP address is correct.")
        except Exception as e:
            print(f"❌ Error running ping: {e}")
    
    print("\nTroubleshooting tips:")
    print("1. Make sure Lavalink is running on the Raspberry Pi")
    print("2. Verify Lavalink is configured to listen on all interfaces (address: 0.0.0.0)")
    print("3. Check for any firewalls blocking port 2333")
    print("4. Verify the correct password is being used")

if __name__ == "__main__":
    asyncio.run(main()) 