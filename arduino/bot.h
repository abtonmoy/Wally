class Bot {
    Motor* fr;
    Motor* br;
    Motor* fl;
    Motor* bl;

    float track_width; // in meters
    float wheel_radius; // in meters
    
    public:
        Bot(Motor* _fr, Motor* _br, Motor* _fl, Motor* _bl, float _track_width, float _wheel_radius) {
            fr = _fr;
            br = _br;
            fl = _fl;
            bl = _bl;
            track_width = _track_width;
            wheel_radius = _wheel_radius;
        }

        void drive_straight(float velocity) {
            int dir = velocity < 0 ? -1 : 1;
            float speed = fabs(velocity);

            fr->set_dir(dir);
            fl->set_dir(dir);
            br->set_dir(dir);
            bl->set_dir(dir);
            fr->set_speed(speed);
            fl->set_speed(speed);
            br->set_speed(speed);
            bl->set_speed(speed);
        }

        void reverse(float velocity) {
            float speed = fabs(velocity);
            fr->set_dir(-1);
            fl->set_dir(-1);
            br->set_dir(-1);
            bl->set_dir(-1);
            fr->set_speed(speed);
            fl->set_speed(speed);
            br->set_speed(speed);
            bl->set_speed(speed);
        }

        void stop() {
            drive_straight(0);
        }

        void turn_inplace(float theta /*in rads*/, float speed /*in RPM*/) { //positive theta = counter-clockwise
            
            float distance = (track_width / 2.0f) * fabs(theta);
            float wheel_turn_angle = distance / (wheel_radius); //Distance over radius

            float sign = theta > 0 ? 1 : -1;

            fr->turn_by_angle(sign * wheel_turn_angle, speed);
            br->turn_by_angle(sign * wheel_turn_angle, speed);
            fl->turn_by_angle(-1 * sign * wheel_turn_angle, speed);
            bl->turn_by_angle(-1 * sign * wheel_turn_angle, speed);
      

            
        }

        void turn_while_moving(float turning_radius, float speed) {
            if(fabs(turning_radius) < track_width / 2) {
                return;
            }
            
            fr->set_dir(1);
            fl->set_dir(1);
            br->set_dir(1);
            bl->set_dir(1);

            float v_left;
            float v_right;
            if(turning_radius < 0) {
                turning_radius = -turning_radius; //ensure positive
                v_right = speed * (1 - track_width / (2 * turning_radius));
                v_left = speed * (1 + track_width / (2 * turning_radius));
            } else {
                v_left = speed * (1 - track_width / (2 * turning_radius));
                v_right = speed * (1 + track_width / (2 * turning_radius));
            }
            

            fl->set_speed(v_left);
            bl->set_speed(v_left);

            fr->set_speed(v_right);
            br->set_speed(v_right);
        }

        void drive_m_meters(float displacement, float speed) {
            float angle = displacement / (wheel_radius); //Distance over radius
      
            
            stop();
           
            // right wheels forward or backward
            fr->turn_by_angle(angle, speed);
            br->turn_by_angle(angle, speed);
            fl->turn_by_angle(angle, speed);
            bl->turn_by_angle(angle, speed);
    

        }
    
};