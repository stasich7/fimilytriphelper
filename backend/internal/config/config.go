package config

import "os"

type Config struct {
	Address        string
	FrontendOrigin string
	DatabaseDSN    string
	StaticDir      string
	ToolsPIN       string
}

func Load() Config {
	return Config{
		Address:        getenv("APP_ADDR", ":8080"),
		FrontendOrigin: getenv("APP_FRONTEND_ORIGIN", ""),
		DatabaseDSN:    getenv("DB_DSN", "postgres://family_trip_helper:family_trip_helper@localhost:5432/family_trip_helper?sslmode=disable"),
		StaticDir:      getenv("APP_STATIC_DIR", ""),
		ToolsPIN:       getenv("APP_TOOLS_PIN", "1234"),
	}
}

func getenv(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}

	return fallback
}
