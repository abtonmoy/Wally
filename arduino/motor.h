class Motor {
    
    int dir_pin;
    int pwm_pin;
    int forward_dir;
    float max_speed; //in RPM

    //Things to do with setting position.

    Encoder* enc;
    int curr_desired_angle;
    int encoder_forward;

public:
    Motor(int _DIR_PIN, int _PWM_PIN, int _forward_dir, float _max_speed, int encA,  int encB, int _encoder_forward) {
        pinMode(dir_pin, OUTPUT);
        pinMode(pwm_pin, OUTPUT);

        dir_pin = _DIR_PIN;
        pwm_pin = _PWM_PIN;
        forward_dir = _forward_dir;
        max_speed = _max_speed;

        enc = new Encoder(encA, encB);
        encoder_forward = _encoder_forward;
        
        
     
        set_speed(0.0f);
        digitalWrite(dir_pin, forward_dir);
       
    }

    void set_dir(int dir) {
        //Serial.println(forward_dir);
        
        if (dir == 1) {
            digitalWrite(dir_pin, forward_dir); // forward
        } else if (dir == -1) {
            digitalWrite(dir_pin, !forward_dir); // reverse
            Serial.print("Backwards means: ");
            Serial.println(!forward_dir);
        }
    }

    void set_speed(float speed) {
        speed = constrain(speed, 0, max_speed);

        int signal_from_speed = (int) (speed * (255.0f/max_speed));
        analogWrite(pwm_pin, signal_from_speed);
    }

    void turn_by_angle(float angle, float speed) { // angle in radians

        int steps = round((angle * ENCODER_STEPS_PER_ROTATION) / (2 * PI)); 
        enc->write(0);
        curr_desired_angle = steps * encoder_forward;
        Serial.print("Curr_desired angle starts out as: ");
        Serial.println(curr_desired_angle);
       
        set_dir(angle > 0 ? 1 : -1);
        set_speed(speed);
        //The main loop will check if speed should be set to zero
    }


    void update() {
        int steps =  enc->read();
        //Serial.println(steps);
        if( (curr_desired_angle < 0 && steps <= curr_desired_angle) || (curr_desired_angle > 0 && steps >= curr_desired_angle) ) {
            set_speed(0.0f);
            curr_desired_angle = 0; //neutral state
        } 
    }

};