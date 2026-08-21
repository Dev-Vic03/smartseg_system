from app import create_app
from database.models import db, User, Customer, Segment

def test_wipe():
    app = create_app()
    with app.app_context():
        user = User.query.first()
        if not user:
            print("No user found")
            return
            
        user_id = user.id
        # Add a test customer and segment
        c = Customer(user_id=user_id, name="Test Wipe")
        db.session.add(c)
        db.session.commit()
        
        s = Segment(customer_id=c.id, recency=10, frequency=1, monetary=100.0, segment_name="VIP")
        db.session.add(s)
        db.session.commit()
        
        print(f"Before wipe - Customers: {Customer.query.count()}, Segments: {Segment.query.count()}")
        
        # Run wipe logic
        try:
            customer_ids_query = db.session.query(Customer.id).filter(Customer.user_id == user_id)
            db.session.query(Segment).filter(Segment.customer_id.in_(customer_ids_query)).delete(synchronize_session=False)
            db.session.query(Customer).filter(Customer.user_id == user_id).delete(synchronize_session=False)
            db.session.commit()
            print("Wipe succeeded")
        except Exception as e:
            db.session.rollback()
            print(f"Error wiping: {e}")
            
        print(f"After wipe - Customers: {Customer.query.count()}, Segments: {Segment.query.count()}")

if __name__ == '__main__':
    test_wipe()
