-- Conversations Table
CREATE TABLE IF NOT EXISTS conversations (
    id VARCHAR(255) PRIMARY KEY,
    user_id varchar(255) NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    title TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_message_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Messages Table
CREATE TABLE IF NOT EXISTS messages (
    id VARCHAR(255) PRIMARY KEY,
    conversation_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    sender VARCHAR(50) NOT NULL,  
    agent_id VARCHAR(255),        
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);