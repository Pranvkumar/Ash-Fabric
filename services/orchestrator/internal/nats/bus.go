package natsbus

import (
	"fmt"
	"time"

	"github.com/nats-io/nats.go"
	"github.com/rs/zerolog/log"
)

// Bus wraps a NATS connection with convenience methods.
type Bus struct {
	conn *nats.Conn
	subs []*nats.Subscription
}

// Connect establishes a connection to the NATS server with retries.
func Connect(url string) (*Bus, error) {
	var conn *nats.Conn
	var err error

	for i := 0; i < 10; i++ {
		conn, err = nats.Connect(url,
			nats.MaxReconnects(60),
			nats.ReconnectWait(2*time.Second),
			nats.DisconnectErrHandler(func(_ *nats.Conn, err error) {
				log.Warn().Err(err).Msg("NATS disconnected")
			}),
			nats.ReconnectHandler(func(_ *nats.Conn) {
				log.Info().Msg("NATS reconnected")
			}),
		)
		if err == nil {
			return &Bus{conn: conn}, nil
		}
		log.Warn().Int("attempt", i+1).Err(err).Msg("NATS connection failed, retrying...")
		time.Sleep(2 * time.Second)
	}
	return nil, fmt.Errorf("failed to connect to NATS after 10 attempts: %w", err)
}

// Subscribe registers a handler for a given subject.
func (b *Bus) Subscribe(subject string, handler func(msg []byte)) error {
	sub, err := b.conn.Subscribe(subject, func(m *nats.Msg) {
		log.Debug().Str("subject", m.Subject).Int("size", len(m.Data)).Msg("Message received")
		handler(m.Data)
	})
	if err != nil {
		return fmt.Errorf("subscribe to %s: %w", subject, err)
	}
	b.subs = append(b.subs, sub)
	return nil
}

// Publish sends data to the given subject.
func (b *Bus) Publish(subject string, data []byte) error {
	if err := b.conn.Publish(subject, data); err != nil {
		return fmt.Errorf("publish to %s: %w", subject, err)
	}
	return nil
}

// Request sends a request and waits for a reply (synchronous).
func (b *Bus) Request(subject string, data []byte, timeout time.Duration) ([]byte, error) {
	msg, err := b.conn.Request(subject, data, timeout)
	if err != nil {
		return nil, fmt.Errorf("request to %s: %w", subject, err)
	}
	return msg.Data, nil
}

// IsConnected returns true if NATS connection is active.
func (b *Bus) IsConnected() bool {
	return b.conn != nil && b.conn.IsConnected()
}

// Close drains subscriptions and closes the connection.
func (b *Bus) Close() {
	for _, sub := range b.subs {
		_ = sub.Drain()
	}
	b.conn.Close()
	log.Info().Msg("NATS connection closed")
}
