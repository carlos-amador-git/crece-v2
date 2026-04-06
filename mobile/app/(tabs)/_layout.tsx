/**
 * Tab navigator — three tabs: Encuestas, Rutas, Perfil.
 */

import { Tabs } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { Colors } from "@/constants/theme";

type IoniconsName = React.ComponentProps<typeof Ionicons>["name"];

function TabIcon({
  name,
  color,
  size,
}: {
  name: IoniconsName;
  color: string;
  size: number;
}) {
  return <Ionicons name={name} size={size} color={color} />;
}

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: Colors.primary },
        headerTintColor: Colors.white,
        headerTitleStyle: { fontWeight: "700" },
        tabBarActiveTintColor: Colors.primary,
        tabBarInactiveTintColor: Colors.gray400,
        tabBarStyle: {
          borderTopColor: Colors.gray200,
          paddingBottom: 4,
          height: 56,
        },
        tabBarLabelStyle: {
          fontSize: 12,
          fontWeight: "600",
        },
      }}
    >
      <Tabs.Screen
        name="dashboard"
        options={{
          title: "Panel",
          tabBarIcon: ({ color, size }) => (
            <TabIcon name="grid-outline" color={color} size={size} />
          ),
          tabBarAccessibilityLabel: "Panel general",
        }}
      />
      <Tabs.Screen
        name="diagnostico"
        options={{
          title: "IPD",
          tabBarIcon: ({ color, size }) => (
            <TabIcon name="analytics-outline" color={color} size={size} />
          ),
          tabBarAccessibilityLabel: "Diagnostico digital",
        }}
      />
      <Tabs.Screen
        name="encuestas"
        options={{
          title: "Encuestas",
          tabBarIcon: ({ color, size }) => (
            <TabIcon name="clipboard-outline" color={color} size={size} />
          ),
          tabBarAccessibilityLabel: "Encuestas",
        }}
      />
      <Tabs.Screen
        name="rutas"
        options={{
          title: "Rutas",
          tabBarIcon: ({ color, size }) => (
            <TabIcon name="map-outline" color={color} size={size} />
          ),
          tabBarAccessibilityLabel: "Rutas de canvassing",
        }}
      />
      <Tabs.Screen
        name="perfil"
        options={{
          title: "Perfil",
          tabBarIcon: ({ color, size }) => (
            <TabIcon name="person-outline" color={color} size={size} />
          ),
          tabBarAccessibilityLabel: "Mi perfil",
        }}
      />
    </Tabs>
  );
}
